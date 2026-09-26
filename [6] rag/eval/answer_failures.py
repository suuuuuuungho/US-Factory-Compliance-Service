"""SUU-149: 답변 실패(Subpart 0 · 심판 0 · 근거율<1)를 원인 하나로 태그한다. $0, API 없음.

사용법 (레포 루트에서):
  python "[6] rag/eval/answer_failures.py" [--run-id 2026-09-19_answer_v2_gpt-5-mini]
  → 태그별 건수·case_id 표 + 케이스별 한 줄. 파일에 쓰지 않는다(문서에 사람이 옮김)

태그(우선순위 순): fabricated(넘겨준 조문 밖 인용) > search(정답 조문이 given에 없음)
  > format(subpart 칸이 코드가 아님) > answer(Subpart 잘못 골랐거나 심판 0)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "[2] db/pipeline/5_rag"))
from ecfr_answer_score import normalize_subpart  # noqa: E402
from ecfr_eval import citation_section_key  # noqa: E402

SUBPART_CODE = re.compile(r"^[A-Z]{1,7}$")
TAGS = ("fabricated", "search", "format", "answer")
TAGS_V2 = ("format", "fabricated", "quote_mismatch", "search", "answer")


def _candidate_subparts(out: dict) -> list[str]:
    answer = out.get("answer") or {}
    return [str(c.get("subpart")) for c in answer.get("candidates", [])]


def classify(out: dict, case: dict) -> str | None:
    if not (out["subpart"] == 0 or out["judge"] == 0 or out["citation_grounded"] < 1):
        return None
    if out["outside_citations"]:
        return "fabricated"
    gold = {citation_section_key(c) for c in case["gold_citations"]}
    if not gold & set(out["given"]):
        return "search"
    if out["subpart"] == 0 and any(not SUBPART_CODE.match(normalize_subpart(s)) for s in _candidate_subparts(out)):
        return "format"
    return "answer"


def classify_v2(out: dict, case: dict) -> str | None:
    if out["answer"] is None:
        return "format"
    if out["g0_outside"]:
        return "fabricated"
    if out["g1_mismatched"]:
        return "quote_mismatch"
    if out["g2_subpart"] == 0:
        gold = {citation_section_key(c) for c in case["gold_citations"]}
        return "answer" if gold & set(out["given"]) else "search"
    return None


def summarize(outs: list[dict], classify_fn, tags: tuple[str, ...] = TAGS) -> dict:
    cases = {tag: [] for tag in tags}
    for o in outs:
        tag = classify_fn(o)
        if tag is not None:
            cases[tag].append(o["case_id"])
    return {"n_failed": sum(len(v) for v in cases.values()),
            "counts": {tag: len(cases[tag]) for tag in tags}, "cases": cases}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="2026-09-19_answer_v2_gpt-5-mini")
    args = ap.parse_args()
    read = lambda p: [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]  # noqa: E731
    outs = read(HERE / "results" / f"{args.run_id}.jsonl")
    cases = {c["case_id"]: c for c in read(HERE / "rag_eval_case_v2.jsonl")}

    v2 = bool(outs and outs[0].get("scorer_version") == "v2")
    classify_fn, tags = (classify_v2, TAGS_V2) if v2 else (classify, TAGS)
    table = summarize(outs, lambda o: classify_fn(o, cases[o["case_id"]]), tags=tags)
    print(f"{args.run_id}: failed {table['n_failed']}/{len(outs)}")
    print("| 태그 | 건수 | case_id |")
    print("|---|---|---|")
    for tag in tags:
        print(f"| {tag} | {table['counts'][tag]} | {', '.join(table['cases'][tag])} |")
    print()
    for o in outs:
        case = cases[o["case_id"]]
        tag = classify_fn(o, case)
        if tag is None:
            continue
        gold = {citation_section_key(c) for c in case["gold_citations"]}
        metric = f"g1 {o['g1_quote']:.2f} g4 {o['g4_checklist']:.2f}" if v2 else f"judge {o['judge']}"
        print(f"{o['case_id']}, {tag}, gold {case['gold_subparts']}, 후보 {_candidate_subparts(o)}, "
              f"gold in given {len(gold & set(o['given']))}/{len(gold)}, {metric}")


if __name__ == "__main__":
    main()
