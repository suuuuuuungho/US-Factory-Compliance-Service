"""SUU-134: 저장된 hybrid 순위(ranked_all)를 검색 코드의 규칙으로 다시 채점하면 SUU-132 시뮬(0.631)과 같다."""
import json
import sys
from pathlib import Path

RAG = Path(__file__).parents[1]
sys.path[:0] = [str(RAG / "eval"), str(RAG.parent / "[2] db/pipeline/5_rag")]

from ecfr_search import RULES, apply_rank_rules  # noqa: E402
from sweep_rules import score  # noqa: E402

RESULT = RAG / "eval/results/2026-09-18_hybrid_v2.jsonl"


def test_replay_matches_simulation():
    lines = [json.loads(l) for l in RESULT.read_text(encoding="utf-8").splitlines() if l.strip()]
    ndcg = []
    for line in lines:
        sections = [{"section_key": k, "subpart": sp, "score": s} for k, sp, s in line["ranked_all"]]
        ranked = [[s["section_key"], s["subpart"]] for s in apply_rank_rules(sections, **RULES)]
        ndcg.append(score(line["gold_sections"], ranked)["ndcg@10"])
    assert len(lines) == 102
    assert round(sum(ndcg) / len(ndcg), 3) == 0.631
