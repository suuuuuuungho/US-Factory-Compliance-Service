"""RAGAS로 저장된 답 run을 평가한다(실험). 새 답은 만들지 않고, 심판 LLM 호출만 한다.

입력(케이스마다):
- user_input: rag_eval_case_v2.jsonl의 question
- response: run 파일의 answer(JSON)를 문장으로 풀어 쓴 것 (subpart · criteria · checklist)
- retrieved_contexts: run 파일의 given(넘겨준 조문) 전문 = cache/section_texts.json
- reference: notes + gold_subparts + gold_citations

지표 5개(ragas.metrics.collections): faithfulness, answer_relevancy, context_precision, context_recall, answer_correctness.
결과: results/<run_id>_ragas.jsonl (케이스별 점수) + 평균·토큰·비용 출력.

    python "[6] rag/eval/run_ragas.py" --limit 2      # 맛보기
    python "[6] rag/eval/run_ragas.py"                # 102건
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import httpx
from openai import AsyncOpenAI

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from llm_rerank import PRICE_PER_M  # noqa: E402
from run_eval import load_env  # noqa: E402

RESULTS = HERE / "results"
CASES = HERE / "rag_eval_case_v2.jsonl"
TEXTS_CACHE = HERE / "cache" / "section_texts.json"
DEFAULT_RUN = "2026-09-19_answer_v2_gpt-5-mini_top10"
METRICS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall", "answer_correctness")


def answer_to_text(answer: dict | None, raw: str) -> str:
    """답 JSON → 심판이 읽을 문장. 파싱 실패면 raw 그대로."""
    if not answer:
        return raw or ""
    lines = []
    for c in answer.get("candidates", []):
        lines.append(f"Candidate subpart: 40 CFR Part 63 Subpart {c.get('subpart')} ({c.get('title', '')}).")
        for cr in c.get("criteria", []):
            cites = ", ".join(cr.get("citations", []))
            lines.append(f"- {cr.get('criterion', '')} [{cites}]")
    if answer.get("checklist"):
        lines.append("Checklist for the operator:")
        lines += [f"- {item}" for item in answer["checklist"]]
    return "\n".join(lines)


def reference_text(case: dict) -> str:
    return (f"{case['notes']} Applicable subpart(s): {', '.join(case['gold_subparts']) or 'none'}. "
            f"Key provisions: {', '.join(case['gold_citations'])}.")


def usage_client(usage: dict) -> AsyncOpenAI:
    """응답 usage를 합산하는 OpenAI 클라이언트."""
    async def on_response(resp: httpx.Response) -> None:
        if "application/json" not in resp.headers.get("content-type", ""):
            return
        body = json.loads(await resp.aread())
        u = body.get("usage") or {}
        usage["prompt_tokens"] += u.get("prompt_tokens", 0)
        usage["completion_tokens"] += u.get("completion_tokens", 0)
        usage["calls"] += 1

    http = httpx.AsyncClient(event_hooks={"response": [on_response]}, timeout=120)
    # 429(분당 토큰 한도 200k)는 openai 클라이언트가 지수 백오프로 재시도한다
    return AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], http_client=http, max_retries=10)


async def with_retry(make_coro, tries: int = 8):
    """429(분당 토큰 한도)면 기다렸다 다시. instructor가 openai 클라이언트 재시도를 건너뛰어 직접 한다."""
    for i in range(tries):
        try:
            return await make_coro()
        except Exception as e:
            if "429" not in str(e) or i == tries - 1:
                raise
            await asyncio.sleep(15 * (i + 1))


async def score_case(metrics: dict, case: dict, row: dict, texts: dict, sem: asyncio.Semaphore, prev: dict | None = None) -> dict:
    """prev(이전 결과)가 있으면 None인 지표만 다시 잰다."""
    q, resp, ref = case["question"], answer_to_text(row.get("answer"), row.get("raw_answer", "")), reference_text(case)
    ctx = [texts[k] for k in row["given"] if k in texts]
    makers = {
        "faithfulness": lambda: metrics["faithfulness"].ascore(user_input=q, response=resp, retrieved_contexts=ctx),
        "answer_relevancy": lambda: metrics["answer_relevancy"].ascore(user_input=q, response=resp),
        "context_precision": lambda: metrics["context_precision"].ascore(user_input=q, reference=ref, retrieved_contexts=ctx),
        "context_recall": lambda: metrics["context_recall"].ascore(user_input=q, retrieved_contexts=ctx, reference=ref),
        "answer_correctness": lambda: metrics["answer_correctness"].ascore(user_input=q, response=resp, reference=ref),
    }
    out = {"case_id": case["case_id"], "n_contexts": len(ctx)}
    if prev:
        out.update({m: prev.get(m) for m in METRICS})
        makers = {m: f for m, f in makers.items() if prev.get(m) is None}
    async with sem:
        results = await asyncio.gather(*(with_retry(f) for f in makers.values()), return_exceptions=True)  # 지표들 동시에
    for name, r in zip(makers, results):
        if isinstance(r, Exception):  # 한 지표 실패가 케이스 전체를 막지 않게
            out[name] = None
            out.setdefault("errors", []).append(f"{name}: {type(r).__name__}: {str(r)[:200]}")
        else:
            out[name] = float(r.value)
    print(f"{out['case_id']}: " + " ".join(f"{m}={out[m]:.2f}" if out[m] is not None else f"{m}=ERR" for m in METRICS), flush=True)
    return out


def summarize(outs: list[dict]) -> dict:
    return {m: round(sum(o[m] for o in outs if o[m] is not None) / max(1, sum(o[m] is not None for o in outs)), 3) for m in METRICS}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=DEFAULT_RUN)
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--limit", type=int, default=0, help="앞에서 N건만(맛보기)")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=16000, help="심판 호출 출력 상한(추론 포함)")
    ap.add_argument("--reasoning-effort", default="minimal", help="gpt-5 계열만. 빈 문자열이면 안 보냄")
    ap.add_argument("--retry-missing", action="store_true", help="결과 파일에서 None인 지표만 다시 잰다")
    args = ap.parse_args()
    load_env()

    from ragas.embeddings import OpenAIEmbeddings
    from ragas.llms import llm_factory
    from ragas.metrics.collections import AnswerCorrectness, AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness

    usage = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}
    client = usage_client(usage)
    extra = {"reasoning_effort": args.reasoning_effort} if args.reasoning_effort else {}
    # gpt-5-mini는 추론 토큰이 출력 상한에 포함 → 기본 1024면 끊김. reasoning_effort=minimal이면 생각을 거의 안 해 빠르고 싸다
    llm = llm_factory(args.model, client=client, max_tokens=args.max_tokens, **extra)
    emb = OpenAIEmbeddings(client=client)
    metrics = {
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": AnswerRelevancy(llm=llm, embeddings=emb),
        "context_precision": ContextPrecision(llm=llm),
        "context_recall": ContextRecall(llm=llm),
        "answer_correctness": AnswerCorrectness(llm=llm, embeddings=emb),
    }

    cases = {c["case_id"]: c for c in (json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip())}
    rows = [json.loads(l) for l in (RESULTS / f"{args.run_id}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.limit:
        rows = rows[: args.limit]
    texts = json.loads(TEXTS_CACHE.read_text(encoding="utf-8"))

    out_path = RESULTS / f"{args.run_id}_ragas{'_' + str(args.limit) if args.limit else ''}.jsonl"
    prev = {}
    if args.retry_missing:
        prev = {o["case_id"]: o for o in map(json.loads, out_path.read_text(encoding="utf-8").splitlines()) if o}
        rows = [r for r in rows if any(prev.get(r["case_id"], {}).get(m) is None for m in METRICS)]
        print(f"retry missing: {len(rows)} cases")

    t0 = time.perf_counter()
    sem = asyncio.Semaphore(args.concurrency)
    outs = await asyncio.gather(*(score_case(metrics, cases[r["case_id"]], r, texts, sem, prev.get(r["case_id"])) for r in rows))
    await client.close()
    if prev:  # 다시 잰 것만 갈아 끼우고 순서는 원래대로
        prev.update({o["case_id"]: o for o in outs})
        outs = list(prev.values())

    out_path.write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in outs), encoding="utf-8")
    pin, pout = PRICE_PER_M.get(args.model, (0, 0))
    cost = usage["prompt_tokens"] / 1e6 * pin + usage["completion_tokens"] / 1e6 * pout
    print(f"\n{out_path.name}: {len(outs)} cases, {time.perf_counter() - t0:.0f}s, usage {usage}, cost ${cost:.2f} ({args.model})")
    print("mean:", json.dumps(summarize(outs)))
    errs = [e for o in outs for e in o.get("errors", [])]
    if errs:
        print(f"errors {len(errs)}:", *errs[:5], sep="\n  ")


if __name__ == "__main__":
    asyncio.run(main())
