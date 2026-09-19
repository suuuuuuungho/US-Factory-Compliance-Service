"""SUU-147: 102건 답변 실행기의 순수 부분 — 조문 전문 합치기, 상위 N 고르기, 결과 한 줄, run 기록."""
import sys
from pathlib import Path

RAG = Path(__file__).parents[1]
sys.path.insert(0, str(RAG / "eval"))

from run_answer import ANSWER_RUNS, TOP_N, answer_run_record, join_section_text, score_line, top_sections  # noqa: E402


def test_answer_runs_live_in_their_own_file_not_search_runs():
    # pass_line.py는 runs.jsonl의 최신 hybrid·v2·gpt-5-mini run을 검색 합격선으로 검사한다. 답변 run이 거기 섞이면 CI가 깨진다
    assert ANSWER_RUNS.name == "answer_runs.jsonl"
    assert ANSWER_RUNS.parent == RAG / "eval"


def test_join_section_text_orders_body_pieces_then_tables():
    rows = [
        {"chunk_key": "ecfr/40/63/subpart-PPPP/section-63.4481/1", "chunk_text": "TABLE"},
        {"chunk_key": "ecfr/40/63/subpart-PPPP/section-63.4481/0-1", "chunk_text": "(b) second"},
        {"chunk_key": "ecfr/40/63/subpart-PPPP/section-63.4481/0", "chunk_text": "(a) first"},
    ]
    assert join_section_text(rows) == "(a) first\n\n(b) second\n\nTABLE"


def test_top_sections_takes_first_n_of_saved_llm_order():
    line = {"llm_order": [f"section-63.{i}" for i in range(20)], "ranked_all": [[f"section-63.{i}", "A"] for i in range(20)]}
    assert TOP_N == 5
    top = top_sections(line)
    assert [s["section_key"] for s in top] == [f"section-63.{i}" for i in range(5)]
    assert top[0]["subpart"] == "A"


def test_score_line_has_case_id_answer_four_scores_and_issues():
    case = {"case_id": "c1", "question": "q", "gold_subparts": ["PPPP"], "gold_citations": ["40 CFR 63.4481(a)"], "notes": "n"}
    answer = {"candidates": [{"subpart": "PPPP", "criteria": [{"criterion": "x", "citations": ["40 CFR 63.4481(a)"]}]}], "checklist": ["y"]}
    out = score_line(case, answer, given=["section-63.4481"], issues=[], judge_score=2, judge_text='{"score": 2}')
    assert out["case_id"] == "c1" and out["answer"] == answer
    assert out["subpart"] == 1 and out["citation_recall"] == 1.0 and out["citation_grounded"] == 1.0 and out["judge"] == 2
    assert out["given"] == ["section-63.4481"] and out["issues"] == [] and out["judge_text"] == '{"score": 2}'


def test_answer_run_record_carries_search_run_and_four_means():
    outs = [
        {"case_id": "a", "subpart": 1, "citation_recall": 1.0, "citation_grounded": 1.0, "judge": 2},
        {"case_id": "b", "subpart": 0, "citation_recall": 0.0, "citation_grounded": 0.5, "judge": 0},
    ]
    rec = answer_run_record("2026-09-19_answer_v2_gpt-5-mini", outs, search_run_id="2026-09-18_hybrid_v2_llm_gpt-5-mini",
                            model="gpt-5-mini", judge_model="gpt-5-mini", top_n=5, cost=1.23)
    assert rec["run_id"] == "2026-09-19_answer_v2_gpt-5-mini"
    assert rec["search_run_id"] == "2026-09-18_hybrid_v2_llm_gpt-5-mini"
    assert rec["eval_set_version"] == "v2" and rec["top_n"] == 5
    assert rec["answer_model"] == "gpt-5-mini" and rec["judge_model"] == "gpt-5-mini"
    assert rec["metrics"]["n"] == 2 and rec["metrics"]["judge"] == 1.0 and rec["metrics"]["failed"] == ["b"]
    assert rec["cost_usd"]["total"] == 1.23
    assert rec["run_at"].endswith("Z")


# ---- SUU-152: 조문 수를 --top-n으로 바꿀 수 있다 (기본 5) ----


def test_top_sections_takes_top_n_when_given():
    line = {"llm_order": [f"section-63.{i}" for i in range(20)], "ranked_all": [[f"section-63.{i}", "A"] for i in range(20)]}
    top = top_sections(line, top_n=10)
    assert [s["section_key"] for s in top] == [f"section-63.{i}" for i in range(10)]


def test_top_sections_defaults_to_five():
    line = {"llm_order": [f"section-63.{i}" for i in range(20)], "ranked_all": [[f"section-63.{i}", "A"] for i in range(20)]}
    assert len(top_sections(line)) == TOP_N == 5
