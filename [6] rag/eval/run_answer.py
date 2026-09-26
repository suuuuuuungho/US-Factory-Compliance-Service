"""저장된 검색 결과 → criteria/gates 답변 → 심판 없이 채점기 v2로 채점(SUU-275).
프롬프트·파싱·호출은 `ecfr_answer`, 채점은 `ecfr_answer_score`. 검색은 다시 돌리지 않는다.

사용법 (레포 루트에서):
  python "[6] rag/eval/run_answer.py" [--shape criteria|gates] [--subset] [--top-n 10] [--always-a] [--limit 3] [--workers 8]
  → results/<run_id>.jsonl + answer_runs.jsonl 한 줄 + 점수판·토큰·비용 출력
  --replay: OpenAI를 안 부르고 저장된 v2 raw_answer를 다시 파싱·채점한다($0)
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
from ecfr_answer import MAX_COMPLETION_TOKENS, build_answer_request, call_openai_chat, parse_answer, verify_answer  # noqa: E402
from ecfr_answer_score import aggregate_v2, score_answer_v2  # noqa: E402
from llm_rerank import PRICE_PER_M  # noqa: E402
from run_eval import load_env  # noqa: E402

RESULTS = HERE / "results"
ANSWER_RUNS = HERE / "answer_runs.jsonl"
TEXTS_CACHE = HERE / "cache" / "section_texts.json"
SEARCH_RUN_ID = "2026-09-18_hybrid_v2_llm_gpt-5-mini"
TOP_N = 10
SUBSET_PATH = HERE / "rag_eval_subset.json"
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


def select_cases(lines: list[dict], ids: list[str] | None) -> list[dict]:
    if ids is None:
        return lines
    selected = set(ids)
    return [line for line in lines if line["case_id"] in selected]


def score_line(case: dict, answer: dict | None, *, given: list[str], texts: dict[str, str], issues: list[str],
               tokens: dict, cost_usd: float, latency_s: float) -> dict:
    if answer is None:
        scores = {"case_id": case["case_id"], "scorer_version": "v2", "g0_grounded": 0.0, "g0_outside": [],
                  "g1_quote": 0.0, "g1_mismatched": [], "g2_subpart": 0, "g3_citation_recall": 0.0,
                  "g4_checklist": 0.0, "failed": True}
    else:
        # Criteria checklists contain strings; v2's gate-link metric is zero for that shape.
        scoring_answer = answer if all(isinstance(item, dict) for item in answer.get("checklist", [])) else {
            **answer, "checklist": []
        }
        scores = score_answer_v2(scoring_answer, case, {key: texts[key] for key in given if key in texts})
    return {**scores, "answer": answer, "given": given, "issues": issues, "cost_usd": cost_usd,
            "latency_s": latency_s, "prompt_tokens": tokens["prompt_tokens"],
            "completion_tokens": tokens["completion_tokens"]}


def default_run_id(shape: str, model: str, *, subset: bool, max_completion_tokens: int,
                   verified: bool = False, day: str | None = None) -> str:
    if day is None:
        day = f"{datetime.now(timezone.utc):%Y-%m-%d}"
    return (f"{day}_answer_{shape}_{model}" + ("_subset51" if subset else "")
            + (f"_out{max_completion_tokens // 1000}k" if max_completion_tokens != MAX_COMPLETION_TOKENS else "")
            + ("_verified" if verified else ""))


def answer_run_record(run_id: str, outs: list[dict], *, search_run_id: str, model: str, shape: str, top_n: int,
                      subset: bool, cost: float, always: tuple[str, ...] = (), tokens: dict | None = None,
                      max_completion_tokens: int = MAX_COMPLETION_TOKENS, verified: bool = False) -> dict:
    tokens = tokens or {}
    prompt_tokens = int(tokens.get("prompt_tokens", 0))
    completion_tokens = int(tokens.get("completion_tokens", 0))
    return {
        "run_id": run_id,
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "search_run_id": search_run_id,
        "eval_set_version": "v2",
        "subset": subset,
        "n_cases": len(outs),
        "top_n": top_n,
        "always_sections": list(always),
        "answer_model": model,
        "shape": shape,
        "scorer_version": "v2",
        "tokens": {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "prompt_per_case": prompt_tokens // len(outs) if outs else 0,
        },
        "metrics": aggregate_v2(outs),
        "cost_usd": {"per_query": cost / len(outs) if outs else 0.0, "total": cost},
        "max_completion_tokens": max_completion_tokens,
        "verified": verified,
    }


def write_run_record(path: Path, rec: dict) -> None:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
    for i, old in enumerate(records):
        if old.get("run_id") == rec["run_id"]:
            records[i] = rec
            break
    else:
        records.append(rec)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--shape", choices=("criteria", "gates"), default="criteria")
    ap.add_argument("--subset", action="store_true")
    ap.add_argument("--max-completion-tokens", type=int, default=MAX_COMPLETION_TOKENS)
    ap.add_argument("--top-n", type=int, default=TOP_N)
    ap.add_argument("--always-a", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--replay", action="store_true")
    ap.add_argument("--replay-from")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--retry-empty", action="store_true")
    ap.add_argument("--run-id")
    args = ap.parse_args()
    if args.run_id is None:
        args.run_id = default_run_id(args.shape, args.model, subset=args.subset,
                                     max_completion_tokens=args.max_completion_tokens, verified=args.verify)
    load_env()
    always = ALWAYS_SECTIONS if args.always_a else ()
    out_path = RESULTS / f"{args.run_id}.jsonl"
    saved: dict[str, dict] = {}
    if args.replay or args.replay_from or args.retry_empty:
        saved_path = RESULTS / f"{args.replay_from}.jsonl" if args.replay_from else out_path
        saved = {o["case_id"]: o for o in map(json.loads, filter(None, saved_path.read_text(encoding="utf-8").splitlines()))}
        required = {"raw_answer", "prompt_tokens", "completion_tokens", "cost_usd", "latency_s"}
        if any(o.get("scorer_version") != "v2" or not required <= o.keys() for o in saved.values()):
            raise ValueError("replay/retry requires saved v2 rows with tokens, cost and latency")

    lines = [json.loads(l) for l in (RESULTS / f"{SEARCH_RUN_ID}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    cases = {c["case_id"]: c for c in map(json.loads, filter(None, (HERE / "rag_eval_case_v2.jsonl").read_text(encoding="utf-8").splitlines()))}
    ids = json.loads(SUBSET_PATH.read_text(encoding="utf-8"))["subset"] if args.subset else None
    lines = select_cases(lines, ids)
    lines = lines[: args.limit] if args.limit else lines
    if (args.replay or args.replay_from) and any(line["case_id"] not in saved for line in lines):
        raise ValueError("replay requires a saved row for every selected case")
    texts = fetch_texts(sorted({s["section_key"] for l in lines for s in top_sections(l, args.top_n, always)}))
    pin, pout = PRICE_PER_M.get(args.model, (0, 0))

    def one(line: dict) -> dict:
        case = cases[line["case_id"]]
        sections = top_sections(line, args.top_n, always)
        given = [s["section_key"] for s in sections]
        prev = saved.get(case["case_id"])
        reuse = prev is not None and (args.replay or args.replay_from or (args.retry_empty and prev.get("answer") is not None))
        if reuse:
            raw_answer = prev["raw_answer"]
            tokens = {"prompt_tokens": prev["prompt_tokens"], "completion_tokens": prev["completion_tokens"]}
            cost_usd, latency_s = prev["cost_usd"], prev["latency_s"]
        else:
            request = build_answer_request(case["question"], [{**s, "text": texts[s["section_key"]]} for s in sections],
                                           model=args.model, shape=args.shape,
                                           max_completion_tokens=args.max_completion_tokens)
            start = time.perf_counter()
            response = call_openai_chat(request)
            latency_s = time.perf_counter() - start
            raw_answer = response["text"]
            tokens = {"prompt_tokens": response["prompt_tokens"], "completion_tokens": response["completion_tokens"]}
            cost_usd = tokens["prompt_tokens"] / 1e6 * pin + tokens["completion_tokens"] / 1e6 * pout
        try:
            answer, issues = parse_answer(raw_answer, given, shape=args.shape)
        except ValueError as e:
            answer, issues = None, [f"parse error: {e}"]
        if args.verify and answer is not None:
            answer = verify_answer(answer, given, {k: texts[k] for k in given if k in texts})
        out = score_line(case, answer, given=given, texts=texts, issues=issues, tokens=tokens,
                         cost_usd=cost_usd, latency_s=latency_s)
        out["raw_answer"] = raw_answer
        print(f"  {case['case_id']} g0 {out['g0_grounded']:.2f} g1 {out['g1_quote']:.2f} "
              f"g2 {out['g2_subpart']} g3 {out['g3_citation_recall']:.2f} "
              f"g4 {out['g4_checklist']:.2f} failed {out['failed']}", flush=True)
        return out

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        outs = list(pool.map(one, lines))
    out_path.write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in outs), encoding="utf-8")
    usage = {"prompt_tokens": sum(o["prompt_tokens"] for o in outs),
             "completion_tokens": sum(o["completion_tokens"] for o in outs)}
    cost = sum(o["cost_usd"] for o in outs)
    board = aggregate_v2(outs)
    print(f"{out_path.name}: {len(outs)} cases, {time.perf_counter() - t0:.0f}s, tokens {usage}, cost ${cost:.2f}")
    print("scores:", {k: round(v, 3) for k, v in board.items() if k not in ("n", "failed", "scorer_version")}, "failed", len(board["failed"]))
    print("no answer:", [o["case_id"] for o in outs if o["answer"] is None])
    if not args.limit:
        write_run_record(ANSWER_RUNS, answer_run_record(args.run_id, outs, search_run_id=SEARCH_RUN_ID,
                         model=args.model, shape=args.shape, top_n=args.top_n, subset=args.subset,
                         cost=cost, always=always, tokens=usage, max_completion_tokens=args.max_completion_tokens,
                         verified=args.verify))
        print(f"answer_runs.jsonl updated: {args.run_id}")


if __name__ == "__main__":
    main()
