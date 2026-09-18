"""SUU-132: 리랭크 전체 순위(ranked_all) 저장 + 창·규칙 시뮬레이션."""
import sys
from pathlib import Path

RAG = Path(__file__).parents[1]
sys.path[:0] = [str(RAG / "eval"), str(RAG.parent / "[2] db/pipeline/5_rag")]

from run_eval import ranked_all_of  # noqa: E402
from sweep_rules import GRID, apply_rules, sweep_table  # noqa: E402


def _sec(key, subpart, score=1.0):
    return {"section_key": key, "chunk_key": key, "subpart": subpart, "score": score}


def test_result_line_has_ranked_all():
    sections = [_sec(f"section-63.{i}", "PPPP", 1 - i / 100) for i in range(25)]
    out = ranked_all_of(sections)
    assert len(out) == 25 > 20
    assert out[0] == ["section-63.0", "PPPP", 1.0]


# ranked = [section_key, subpart] 목록 (앞이 1등)
R = [["section-63.4500", "PPPP"], ["appendix-Table-1", "PPPP"], ["section-63.1573", "UUU"],
     ["section-63.8", "A"], ["section-63.4510", "PPPP"], ["section-63.700", "EEE"]]


def test_apply_rules_moves_tables_back():
    out = apply_rules(R, window=6, demote_tables=True, subpart_top=0)
    assert [s for s, _ in out] == ["section-63.4500", "section-63.1573", "section-63.8", "section-63.4510", "section-63.700", "appendix-Table-1"]


def test_apply_rules_prefers_found_subparts_and_A():
    out = apply_rules(R, window=6, demote_tables=False, subpart_top=1)  # 5등 안 Subpart 상위 1개 = PPPP
    assert [s for s, _ in out] == ["section-63.4500", "appendix-Table-1", "section-63.8", "section-63.4510", "section-63.1573", "section-63.700"]


def test_apply_rules_keeps_outside_window():
    out = apply_rules(R, window=3, demote_tables=True, subpart_top=1)
    assert [s for s, _ in out][:3] == ["section-63.4500", "section-63.1573", "appendix-Table-1"]
    assert out[3:] == R[3:]


def test_sweep_table_shape():
    cases = [{"gold": ["section-63.4500", "section-63.8"], "ranked": R}]
    rows = sweep_table(cases)
    assert len(rows) == len(GRID["window"]) * 2 * len(GRID["subpart_top"]) == 30
    assert set(rows[0]) == {"window", "tables", "subpart", "hit@5", "hit@20", "ndcg@10", "recall@20"}
