"""SUU-147: 저장된 기본 조합 검색 결과의 상위 TOP_N 조문 전문 → gpt-5-mini → 판정 기준표 JSON → 4개 지표로 채점.
프롬프트·파싱·호출은 파이프라인 `ecfr_answer`, 채점은 `ecfr_answer_score`(SUU-146). 검색은 다시 돌리지 않는다.

사용법 (레포 루트에서):
  python "[6] rag/eval/run_answer.py" [--model gpt-5-mini] [--judge-model gpt-5-mini] [--top-n 5] [--always-a] [--limit 3] [--workers 8]
  → results/<날짜>_answer_v2_<model>.jsonl + answer_runs.jsonl 한 줄 + 점수판·토큰·비용 출력
  --replay: OpenAI를 안 부르고 저장된 raw_answer·judge_text를 다시 파싱·채점한다($0)
  --retry-empty: 저장 결과 중 answer가 없는(파싱 실패) 케이스만 다시 부른다
  --always-a: 상위 N 뒤에 Subpart A 공통 규칙 63.2·63.7·63.8을 항상 붙인다 (SUU-153)

- 입력: results/<SEARCH_RUN_ID>.jsonl 의 llm_order(hybrid + 규칙 + LLM 리랭크, SUU-136) 앞 TOP_N
- 조문 전문: rag_chunk 그 조문의 청크 전부(본문 /0, /0-1… 먼저, 표 /1, /2… 뒤)를 chunk_text만 이어 붙임. cache/section_texts.json 에 캐시
- 답변 run은 answer_runs.jsonl 에 쓴다. runs.jsonl 은 검색 합격선(pass_line.py)이 검사하므로 섞지 않는다
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "[2] db/pipeline/5_rag"))
from ecfr_answer import build_answer_request, call_openai_chat, parse_answer  # noqa: E402
from ecfr_answer_score import (  # noqa: E402
    aggregate, build_judge_request, parse_judge, score_citation_grounded, score_citation_recall, score_subpart,
)
from llm_rerank import PRICE_PER_M  # noqa: E402
from run_eval import load_env  # noqa: E402

RESULTS = HERE / "results"
ANSWER_RUNS = HERE / "answer_runs.jsonl"
TEXTS_CACHE = HERE / "cache" / "section_texts.json"
SEARCH_RUN_ID = "2026-09-18_hybrid_v2_llm_gpt-5-mini"
TOP_N = 5
ALWAYS_SECTIONS = ("section-63.2", "section-63.7", "section-63.8")  # 정의·성능시험·모니터링. 정답 인용에 가장 자주 나오는 A 조문


def _piece_order(chunk_key: str) -> tuple[int, int]:
    """본문 /0, /0-1, /0-2 … 먼저(숫자 순), 표 /1, /2 … 뒤."""
    piece = chunk_key.rsplit("/", 1)[1]
    if piece.startswith("0"):
        return (0, int(piece.split("-")[1]) if "-" in piece else 0)
    return (1, int(piece))


def join_section_text(rows: list[dict]) -> str:
    return "\n\n".join(r["chunk_text"] for r in sorted(rows, key=lambda r: _piece_order(r["chunk_key"])))


def fetch_texts(section_keys: list[str]) -> dict[str, str]:
    """조문 전문. 캐시에 없는 것만 Supabase에서 읽는다."""
    texts = json.loads(TEXTS_CACHE.read_text(encoding="utf-8")) if TEXTS_CACHE.exists() else {}
    missing = [k for k in section_keys if k not in texts]
    if missing:
        from supabase import create_client
        client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
        release_id = client.table("common_dataset_current").select("release_id").eq("dataset", "ecfr").execute().data[0]["release_id"]
        for i, key in enumerate(missing, 1):
            rows = (client.table("rag_chunk").select("chunk_key,chunk_text").eq("release_id", release_id)
                    .like("chunk_key", f"%/{key}/%").execute().data)
            texts[key] = join_section_text(rows)
            if i % 50 == 0:
                print(f"  texts fetched {i}/{len(missing)}", flush=True)
        TEXTS_CACHE.parent.mkdir(exist_ok=True)
        TEXTS_CACHE.write_text(json.dumps(texts, ensure_ascii=False), encoding="utf-8")
    return texts


def top_sections(line: dict, top_n: int = TOP_N, always: tuple[str, ...] = ()) -> list[dict]:
    subpart = {k: sp for k, sp in line["ranked_all"]}
    top = line["llm_order"][:top_n]
    return ([{"section_key": k, "subpart": subpart.get(k, "?")} for k in top]
            + [{"section_key": k, "subpart": "A"} for k in always if k not in top])


def score_line(case: dict, answer: dict | None, *, given: list[str], issues: list[str], judge_score: int, judge_text: str) -> dict:
    if answer is None:
        subpart, recall, grounded, outside = 0, 0.0, 0.0, []
    else:
        subpart = score_subpart(answer, case)
        recall = score_citation_recall(answer, case)
        grounded, outside = score_citation_grounded(answer, given)
    return {"case_id": case["case_id"], "answer": answer, "given": given, "issues": issues,
            "subpart": subpart, "citation_recall": recall, "citation_grounded": grounded, "outside_citations": outside,
            "judge": judge_score, "judge_text": judge_text}


def answer_run_record(run_id: str, outs: list[dict], *, search_run_id: str, model: str, judge_model: str, top_n: int, cost: float,
                      always: tuple[str, ...] = (), tokens: dict | None = None) -> dict:
    tokens = tokens or {}
    prompt_tokens = int(tokens.get("prompt_tokens", 0))
    completion_tokens = int(tokens.get("completion_tokens", 0))
    return {
        "run_id": run_id,
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "search_run_id": search_run_id,
        "eval_set_version": "v2",
        "n_cases": len(outs),
        "top_n": top_n,
        "always_sections": list(always),
        "answer_model": model,
        "judge_model": judge_model,
        "tokens": {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "prompt_per_case": prompt_tokens // len(outs) if outs else 0,
        },
        "metrics": aggregate(outs),
        "cost_usd": {"per_query": cost / len(outs) if outs else 0.0, "total": cost},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--judge-model", default="gpt-5-mini")
    ap.add_argument("--top-n", type=int, default=TOP_N)
    ap.add_argument("--always-a", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--replay", action="store_true")
    ap.add_argument("--retry-empty", action="store_true")
    ap.add_argument("--run-id", default=f"{datetime.now(timezone.utc):%Y-%m-%d}_answer_v2_{ap.parse_known_args()[0].model}")
    args = ap.parse_args()
    load_env()
    always = ALWAYS_SECTIONS if args.always_a else ()
    out_path = RESULTS / f"{args.run_id}.jsonl"
    saved: dict[str, dict] = {}
    if args.replay or args.retry_empty:
        saved = {o["case_id"]: o for o in map(json.loads, filter(None, out_path.read_text(encoding="utf-8").splitlines()))}

    lines = [json.loads(l) for l in (RESULTS / f"{SEARCH_RUN_ID}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    cases = {c["case_id"]: c for c in map(json.loads, filter(None, (HERE / "rag_eval_case_v2.jsonl").read_text(encoding="utf-8").splitlines()))}
    lines = lines[: args.limit] if args.limit else lines
    texts = {} if args.replay else fetch_texts(sorted({s["section_key"] for l in lines for s in top_sections(l, args.top_n, always)}))

    usage = {"prompt_tokens": 0, "completion_tokens": 0}

    def ask(request: dict) -> str:
        r = call_openai_chat(request)
        usage["prompt_tokens"] += r["prompt_tokens"]
        usage["completion_tokens"] += r["completion_tokens"]
        return r["text"]

    def one(line: dict) -> dict:
        case = cases[line["case_id"]]
        sections = top_sections(line, args.top_n, always)
        given = [s["section_key"] for s in sections]
        prev = saved.get(case["case_id"])
        reuse = prev is not None and (args.replay or (args.retry_empty and prev.get("answer") is not None))
        if reuse:
            raw_answer, judge_text = prev["raw_answer"], prev["judge_text"]
        else:
            raw_answer = ask(build_answer_request(case["question"], [{**s, "text": texts[s["section_key"]]} for s in sections], model=args.model))
            judge_text = ""
        try:
            answer, issues = parse_answer(raw_answer, given)
        except ValueError as e:
            answer, issues = None, [f"parse error: {e}"]
        judge_score = 0
        if answer is not None:
            if not judge_text and not args.replay:
                judge_text = ask(build_judge_request(answer, case, model=args.judge_model))
            try:
                judge_score = parse_judge(judge_text)
            except ValueError as e:
                issues.append(f"judge parse error: {e}")
        out = score_line(case, answer, given=given, issues=issues, judge_score=judge_score, judge_text=judge_text)
        out["raw_answer"] = raw_answer
        print(f"  {case['case_id']} subpart {out['subpart']} recall {out['citation_recall']:.2f} grounded {out['citation_grounded']:.2f} judge {out['judge']}", flush=True)
        return out

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        outs = list(pool.map(one, lines))
    out_path.write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in outs), encoding="utf-8")
    pin, pout = PRICE_PER_M.get(args.model, (0, 0))
    cost = usage["prompt_tokens"] / 1e6 * pin + usage["completion_tokens"] / 1e6 * pout
    board = aggregate(outs)
    print(f"{out_path.name}: {len(outs)} cases, {time.perf_counter() - t0:.0f}s, tokens {usage}, cost ${cost:.2f}")
    print("scores:", {k: round(v, 3) for k, v in board.items() if k not in ("n", "failed")}, "failed", len(board["failed"]))
    print("no answer:", [o["case_id"] for o in outs if o["answer"] is None])
    if not args.limit:
        with ANSWER_RUNS.open("a", encoding="utf-8") as f:
            f.write(json.dumps(answer_run_record(args.run_id, outs, search_run_id=SEARCH_RUN_ID, model=args.model,
                                                 judge_model=args.judge_model, top_n=args.top_n, cost=cost, always=always,
                                                 tokens=usage), ensure_ascii=False) + "\n")
        print(f"answer_runs.jsonl += {args.run_id}")


if __name__ == "__main__":
    main()
