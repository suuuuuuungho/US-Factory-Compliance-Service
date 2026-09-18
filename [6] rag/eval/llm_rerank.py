"""SUU-135: 저장된 hybrid+규칙 상위 20조문을 OpenAI LLM으로 다시 줄 세워 채점한다.
프롬프트·파싱·호출은 파이프라인 `ecfr_llm_rerank`(SUU-136)에 있고 여기서는 저장된 순위에 그것을 되돌린다.

사용법 (레포 루트에서):
  python "[6] rag/eval/llm_rerank.py" --run-id 2026-09-18_hybrid_v2 [--model gpt-5-mini] [--limit 3] [--workers 8]
  → results/<run-id>_llm_<model>.jsonl + runs.jsonl 한 줄 + 점수판·토큰·비용 출력
  --replay: OpenAI를 안 부르고 저장된 results/<run-id>_llm_<model>.jsonl의 답을 다시 쓴다($0, SUU-137 runs.jsonl 기록용)

- 입력: results/<run-id>.jsonl 의 ranked_all(Kanon 리랭크 전체 순위) → 규칙(SUU-134) → 상위 TOP_N 조문
- 조문 본문: rag_chunk 첫 body 청크(chunk_key …/<section_key>/0)의 context_text + chunk_text 앞 HEAD_CHARS자.
  cache/section_heads.json 에 캐시(Supabase 읽기만).
- LLM은 상위 TOP_N 안의 순서만 바꾼다. 답에 빠진 조문은 원래 순서로 뒤에 붙인다.
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "[2] db/pipeline/5_rag"))
from ecfr_llm_rerank import HEAD_CHARS, LLM_TOP_N as TOP_N, call_openai_rerank_api, llm_rerank_sections, parse_ranking  # noqa: E402,F401
from ecfr_llm_rerank import build_llm_rerank_prompt as build_rerank_prompt  # noqa: E402,F401
from ecfr_eval import summarize  # noqa: E402
from ecfr_search import RULES, apply_rank_rules  # noqa: E402
from run_eval import K_MAX, RUNS, load_env  # noqa: E402
from sweep_rules import score  # noqa: E402

RESULTS = HERE / "results"
HEADS_CACHE = HERE / "cache" / "section_heads.json"
PRICE_PER_M = {"gpt-4o-mini": (0.15, 0.60), "gpt-5-mini": (0.25, 2.00)}  # (input, output) USD per 1M tokens


def ruled_sections(line: dict) -> list[dict]:
    """ranked_all → 규칙(SUU-134) 적용한 조문 순위 전체."""
    sections = [{"section_key": k, "subpart": sp, "score": s} for k, sp, s in line["ranked_all"]]
    return apply_rank_rules(sections, **RULES)


def top_sections(line: dict) -> list[dict]:
    return ruled_sections(line)[:TOP_N]


def rerank_line(line: dict, ask, *, heads: dict[str, str]) -> dict:
    """한 케이스: ask(prompt) -> 답 텍스트. 상위 TOP_N만 LLM 순서로 바꾼 ranked_all을 돌려준다."""
    answers: list[str] = []

    def remember(prompt: str) -> str:
        answers.append(ask(prompt))
        return answers[-1]

    ranked = llm_rerank_sections(line.get("question", ""), ruled_sections(line), remember, texts=heads)
    order = [s["section_key"] for s in ranked[:TOP_N]]
    return {"case_id": line["case_id"], "gold_sections": line["gold_sections"], "llm_order": order,
            "ranked_all": [[s["section_key"], s["subpart"]] for s in ranked], "answer": answers[0] if answers else ""}


def fetch_heads(section_keys: list[str]) -> dict[str, str]:
    """조문별 첫 body 청크의 context_text + chunk_text 앞부분. 캐시에 없는 것만 Supabase에서 읽는다."""
    heads = json.loads(HEADS_CACHE.read_text(encoding="utf-8")) if HEADS_CACHE.exists() else {}
    missing = [k for k in section_keys if k not in heads]
    if missing:
        from supabase import create_client
        client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
        release_id = client.table("common_dataset_current").select("release_id").eq("dataset", "ecfr").execute().data[0]["release_id"]
        for i, key in enumerate(missing, 1):
            rows = (client.table("rag_chunk").select("context_text,chunk_text").eq("release_id", release_id)
                    .like("chunk_key", f"%/{key}/0").limit(1).execute().data)
            text = f"{rows[0].get('context_text') or ''}\n{rows[0]['chunk_text']}" if rows else ""
            heads[key] = text[:HEAD_CHARS]
            if i % 50 == 0:
                print(f"  heads fetched {i}/{len(missing)}", flush=True)
        HEADS_CACHE.parent.mkdir(exist_ok=True)
        HEADS_CACHE.write_text(json.dumps(heads, ensure_ascii=False), encoding="utf-8")
    return heads


def scoreboard(lines: list[dict]) -> dict:
    scores = [score(l["gold_sections"], l["ranked_all"]) for l in lines]
    board = {m: round(sum(s[m] for s in scores) / len(scores), 3) for m in ("hit@5", "hit@20", "ndcg@10", "recall@20")}
    board["miss@20"] = [l["case_id"] for l, s in zip(lines, scores) if not s["hit@20"]]
    return board


def run_record(run_id: str, model: str, lines: list[dict], outs: list[dict], base: dict, *, cost: float, replay: bool) -> dict:
    """runs.jsonl 한 줄. 채점은 run_eval과 같은 summarize(상위 K_MAX)로 한다."""
    results = []
    for line, out in zip(lines, outs):
        top = out["ranked_all"][:K_MAX]
        keys = [k for k, _ in top]
        results.append({
            "gold_ranks": {g: keys.index(g) + 1 if g in keys else None for g in line["gold_sections"]},
            "gold_subparts": line["gold_subparts"],
            "returned_subparts": [sp for _, sp in top],
        })
    return {
        "run_id": run_id,
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": base["config"],
        "eval_set_version": base["eval_set_version"],
        "n_cases": len(results),
        "release_id": base["release_id"],
        "embed_model": base.get("embed_model", "kanon-2-embedder"),
        "with_context": base.get("with_context", True),
        "rerank_model": base["rerank_model"],
        "rules": True,
        "llm_model": model,
        "contextualizer_model": base["contextualizer_model"],
        "context_prompt_version": base["context_prompt_version"],
        "chunk_rule_commit": base["chunk_rule_commit"],
        "k_max": K_MAX,
        "metrics": summarize(results, k_max=K_MAX),
        "cost_usd": {"per_query": cost / len(results), "total": cost},
        "notes": f"{base['run_id']} ranked_all → rules → top {TOP_N} reranked by {model}" + (" (replayed saved answers)" if replay else ""),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--replay", action="store_true")
    args = ap.parse_args()
    load_env()
    out_path = RESULTS / f"{args.run_id}_llm_{args.model}.jsonl"
    saved = {}
    if args.replay:
        saved = {o["case_id"]: o["answer"] for o in map(json.loads, filter(None, out_path.read_text(encoding="utf-8").splitlines()))}

    lines = [json.loads(l) for l in (RESULTS / f"{args.run_id}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    cases = [json.loads(l) for l in (HERE / "rag_eval_case_v2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    questions = {c["case_id"]: c["question"] for c in cases}
    for line in lines:
        line["question"] = questions[line["case_id"]]
    lines = lines[: args.limit] if args.limit else lines
    heads = {} if args.replay else fetch_heads(sorted({s["section_key"] for l in lines for s in top_sections(l)}))

    usage = {"prompt_tokens": 0, "completion_tokens": 0}

    def ask(prompt: str) -> str:
        r = call_openai_rerank_api(prompt, model=args.model)
        usage["prompt_tokens"] += r["prompt_tokens"]
        usage["completion_tokens"] += r["completion_tokens"]
        return r["text"]

    t0 = time.perf_counter()

    def one(line):
        out = rerank_line(line, (lambda prompt: saved[line["case_id"]]) if args.replay else ask, heads=heads)
        out["run_id"] = f"{args.run_id}_llm_{args.model}"
        out["model"] = args.model
        print(f"  {line['case_id']} ndcg {score(out['gold_sections'], out['ranked_all'])['ndcg@10']:.2f}", flush=True)
        return out

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        outs = list(pool.map(one, lines))
    out_path.write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in outs), encoding="utf-8")
    pin, pout = PRICE_PER_M.get(args.model, (0, 0))
    cost = usage["prompt_tokens"] / 1e6 * pin + usage["completion_tokens"] / 1e6 * pout
    print(f"{out_path.name}: {len(outs)} cases, {time.perf_counter() - t0:.0f}s, tokens {usage}, cost ${cost:.2f} ({args.model})")
    before = [{"case_id": l["case_id"], "gold_sections": l["gold_sections"], "ranked_all": [[s["section_key"], s["subpart"]] for s in ruled_sections(l)]} for l in lines]
    print("before:", scoreboard(before))
    print("after: ", scoreboard(outs))
    if not args.limit:
        base = next(r for r in map(json.loads, filter(None, RUNS.read_text(encoding="utf-8").splitlines())) if r["run_id"] == args.run_id)
        with RUNS.open("a", encoding="utf-8") as f:
            f.write(json.dumps(run_record(out_path.stem, args.model, lines, outs, base, cost=cost, replay=args.replay), ensure_ascii=False) + "\n")
        print(f"runs.jsonl += {out_path.stem}")


if __name__ == "__main__":
    main()
