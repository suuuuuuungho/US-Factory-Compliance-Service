"""SUU-138: 기본 조합 검색 결과의 상위 조문으로 판정 기준표 답을 만들고 채점한다.

사용법 (레포 루트에서):
  python "[6] rag/eval/run_answer.py" --run-id 2026-09-18_hybrid_v2_llm_gpt-5-mini [--model gpt-5-mini] [--top-k 5] [--limit 3] [--workers 4] [--retry-empty]
  → results/<run-id>_answer_<model>.jsonl + 점수판·토큰·비용 출력

- 입력: results/<run-id>.jsonl 의 ranked_all 상위 top_k 조문 + rag_eval_case_v2.jsonl 의 질문·정답
- 조문 전문: rag_chunk 의 그 조문 청크(chunk_text)를 순서대로 이어 붙임(SECTION_CHARS 상한). cache/section_texts.json 에 캐시(Supabase 읽기만)
- 채점($0): subpart_hit(정답 Subpart가 후보에), citation_recall(정답 조문이 기준 인용에), citation_grounded(인용이 준 조문 안에)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "[2] db/pipeline/5_rag"))
from ecfr_answer import SECTION_CHARS, build_answer_prompt, call_openai_answer_api, parse_answer, score_answer  # noqa: E402
from run_eval import load_env  # noqa: E402

RESULTS = HERE / "results"
TEXTS_CACHE = HERE / "cache" / "section_texts.json"
PRICE_PER_M = {"gpt-5-mini": (0.25, 2.00)}


def fetch_section_texts(section_keys: list[str]) -> dict[str, str]:
    """조문별 청크 본문을 이어 붙인 전문(상한 SECTION_CHARS). 캐시에 없는 것만 Supabase에서 읽는다."""
    texts = json.loads(TEXTS_CACHE.read_text(encoding="utf-8")) if TEXTS_CACHE.exists() else {}
    missing = [k for k in section_keys if k not in texts]
    if missing:
        from supabase import create_client
        client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
        release_id = client.table("common_dataset_current").select("release_id").eq("dataset", "ecfr").execute().data[0]["release_id"]
        for i, key in enumerate(missing, 1):
            rows = (client.table("rag_chunk").select("chunk_key,chunk_text").eq("release_id", release_id)
                    .like("chunk_key", f"%/{key}/%").order("chunk_key").execute().data)
            texts[key] = "\n".join(r["chunk_text"] for r in rows)[:SECTION_CHARS]
            if i % 50 == 0:
                print(f"  texts fetched {i}/{len(missing)}", flush=True)
        TEXTS_CACHE.parent.mkdir(exist_ok=True)
        TEXTS_CACHE.write_text(json.dumps(texts, ensure_ascii=False), encoding="utf-8")
    return texts


def scoreboard(lines: list[dict]) -> dict:
    n = len(lines)
    return {
        "subpart_hit": round(sum(l["score"]["subpart_hit"] for l in lines) / n, 3),
        "citation_recall": round(sum(l["score"]["citation_recall"] for l in lines) / n, 3),
        "citation_grounded": round(sum(l["score"]["citation_grounded"] for l in lines) / n, 3),
        "criteria_per_case": round(sum(l["score"]["n_criteria"] for l in lines) / n, 1),
        "empty": [l["case_id"] for l in lines if not l["answer"]["candidates"]],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--retry-empty", action="store_true", help="저장된 결과에서 후보가 빈 케이스만 다시 묻고 합친다")
    args = ap.parse_args()
    load_env()

    cases = {c["case_id"]: c for c in map(json.loads, filter(None, (HERE / "rag_eval_case_v2.jsonl").read_text(encoding="utf-8").splitlines()))}
    lines = list(map(json.loads, filter(None, (RESULTS / f"{args.run_id}.jsonl").read_text(encoding="utf-8").splitlines())))
    lines = all_lines = lines[: args.limit] if args.limit else lines
    out_path = RESULTS / f"{args.run_id}_answer_{args.model}.jsonl"
    kept = {}
    if args.retry_empty:
        kept = {o["case_id"]: o for o in map(json.loads, filter(None, out_path.read_text(encoding="utf-8").split("\n"))) if o["answer"]["candidates"]}  # 답 안에 U+2028 같은 줄 구분 문자가 있어 splitlines()는 못 쓴다
        lines = [l for l in lines if l["case_id"] not in kept]
        print(f"retrying {len(lines)} empty cases, keeping {len(kept)}")
    for line in lines:
        line["top"] = [{"section_key": k, "subpart": sp} for k, sp in line["ranked_all"][: args.top_k]]
    texts = fetch_section_texts(sorted({s["section_key"] for l in lines for s in l["top"]}))
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    t0 = time.perf_counter()

    def one(line):
        case = cases[line["case_id"]]
        sections = [{**s, "text": texts.get(s["section_key"], "")} for s in line["top"]]
        r = call_openai_answer_api(build_answer_prompt(case["question"], sections), model=args.model)
        usage["prompt_tokens"] += r["prompt_tokens"]
        usage["completion_tokens"] += r["completion_tokens"]
        answer = parse_answer(r["text"])
        score = score_answer(answer, gold_subparts=case["gold_subparts"], gold_citations=case["gold_citations"],
                             context_keys=[s["section_key"] for s in sections])
        print(f"  {line['case_id']} subpart {score['subpart_hit']} recall {score['citation_recall']:.2f} grounded {score['citation_grounded']:.2f}", flush=True)
        return {"run_id": out_path.stem, "case_id": line["case_id"], "model": args.model, "context_sections": [s["section_key"] for s in sections],
                "gold_subparts": case["gold_subparts"], "gold_citations": case["gold_citations"], "answer": answer, "score": score, "raw": r["text"]}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        outs = list(pool.map(one, lines))
    if kept:
        outs = [kept.get(l["case_id"]) or next(o for o in outs if o["case_id"] == l["case_id"]) for l in all_lines]
    out_path.write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in outs), encoding="utf-8")
    pin, pout = PRICE_PER_M.get(args.model, (0, 0))
    cost = usage["prompt_tokens"] / 1e6 * pin + usage["completion_tokens"] / 1e6 * pout
    print(f"{out_path.name}: {len(outs)} cases, {time.perf_counter() - t0:.0f}s, tokens {usage}, cost ${cost:.2f} ({args.model})")
    print("scoreboard:", scoreboard(outs))


if __name__ == "__main__":
    main()
