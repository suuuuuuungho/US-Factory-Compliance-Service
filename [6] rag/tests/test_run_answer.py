"""SUU-147: 답변 실행기의 순수 부분 — 조문 전문 합치기, 상위 N 고르기, 결과 한 줄, run 기록.
SUU-275: 심판 없이 채점기 v2로, 선별셋 51건, 답 모양(criteria/gates)을 run에 남긴다.
"""
import json
import sys
from pathlib import Path

RAG = Path(__file__).parents[1]
sys.path.insert(0, str(RAG / "eval"))

from run_answer import (  # noqa: E402
    ANSWER_RUNS, RESULTS, SUBSET_PATH, TOP_N, answer_run_record, join_section_text, score_line, select_cases, top_sections,
    write_run_record,
)


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
    top = top_sections(line, top_n=5)
    assert [s["section_key"] for s in top] == [f"section-63.{i}" for i in range(5)]
    assert top[0]["subpart"] == "A"


# ---- SUU-152: 조문 수를 --top-n으로 바꿀 수 있다. SUU-275: 기본 10 (계획 [6]-3) ----


def test_top_sections_takes_top_n_when_given():
    line = {"llm_order": [f"section-63.{i}" for i in range(20)], "ranked_all": [[f"section-63.{i}", "A"] for i in range(20)]}
    top = top_sections(line, top_n=10)
    assert [s["section_key"] for s in top] == [f"section-63.{i}" for i in range(10)]


def test_top_sections_defaults_to_ten():
    line = {"llm_order": [f"section-63.{i}" for i in range(20)], "ranked_all": [[f"section-63.{i}", "A"] for i in range(20)]}
    assert len(top_sections(line)) == TOP_N == 10


# ---- SUU-153: Subpart A 63.2·63.7·63.8을 항상 붙인다 (--always-a) ----


def _line(keys):
    return {"llm_order": keys, "ranked_all": [[k, "X"] for k in keys]}


def test_always_sections_are_appended_after_top_n_without_duplicates():
    from run_answer import ALWAYS_SECTIONS

    assert ALWAYS_SECTIONS == ("section-63.2", "section-63.7", "section-63.8")
    # 상위 10 안에 63.7이 이미 있으면 다시 붙이지 않는다
    keys = [f"section-63.{i}" for i in range(100, 109)] + ["section-63.7"] + ["section-63.200"]
    top = top_sections(_line(keys), top_n=10, always=ALWAYS_SECTIONS)
    got = [s["section_key"] for s in top]
    assert got == keys[:10] + ["section-63.2", "section-63.8"]
    assert [s["subpart"] for s in top[-2:]] == ["A", "A"]  # 붙인 조문의 subpart는 A


def test_without_always_top_sections_is_unchanged():
    keys = [f"section-63.{i}" for i in range(100, 120)]
    assert [s["section_key"] for s in top_sections(_line(keys), top_n=10)] == keys[:10]


# ---- SUU-275: 선별셋 51건만 고른다 ----


def test_select_cases_keeps_only_listed_case_ids_in_saved_order():
    lines = [{"case_id": c} for c in ["x1", "x2", "x3", "x4"]]
    assert select_cases(lines, ["x3", "x1", "nope"]) == [{"case_id": "x1"}, {"case_id": "x3"}]
    assert select_cases(lines, None) == lines  # 목록이 없으면 전부


def test_subset_path_is_the_fixed_51_case_file():
    assert SUBSET_PATH == RAG / "eval" / "rag_eval_subset.json"
    assert len(json.loads(SUBSET_PATH.read_text(encoding="utf-8"))["subset"]) == 51


# ---- SUU-275: 결과 한 줄 = 채점기 v2 + 비용·지연. 심판 없음 ----

CASE = {"case_id": "c1", "question": "q", "gold_subparts": ["PPPP"], "gold_citations": ["40 CFR 63.4481(a)"], "notes": "n"}
TEXTS = {"section-63.4481": "§ 63.4481 Am I subject to this subpart? (a) You are subject if you own a source."}
GATES_ANSWER = {
    "candidates": [{"subpart": "PPPP", "title": "t",
                    "gates": [{"type": "affected_source", "question": "q", "test": "t",
                               "citations": ["40 CFR 63.4481(a)"], "quote": "you are subject if you own a source"}],
                    "missing": []}],
    "checklist": [{"item": "i", "gate": "affected_source"}],
}
CRITERIA_ANSWER = {"candidates": [{"subpart": "PPPP", "criteria": [{"criterion": "x", "citations": ["40 CFR 63.4481(a)"]}]}], "checklist": ["y"]}
TOKENS = {"prompt_tokens": 15000, "completion_tokens": 2000}


def test_score_line_uses_scorer_v2_and_keeps_cost_latency_tokens():
    out = score_line(CASE, GATES_ANSWER, given=list(TEXTS), texts=TEXTS, issues=[], tokens=TOKENS, cost_usd=0.0078, latency_s=41.2)
    assert out["case_id"] == "c1" and out["answer"] == GATES_ANSWER and out["given"] == list(TEXTS) and out["issues"] == []
    assert out["scorer_version"] == "v2"
    assert out["g0_grounded"] == 1.0 and out["g1_quote"] == 1.0 and out["g2_subpart"] == 1
    assert out["g3_citation_recall"] == 1.0 and out["g4_checklist"] == 1.0 and out["failed"] is False
    assert out["cost_usd"] == 0.0078 and out["latency_s"] == 41.2
    assert out["prompt_tokens"] == 15000 and out["completion_tokens"] == 2000
    assert "judge" not in out and "judge_text" not in out


def test_score_line_scores_criteria_shape_too_with_zero_g1_g4():
    # 나열 모양은 관문·발췌가 없어 G1·G4가 0. G0·G2·G3는 잰다
    out = score_line(CASE, CRITERIA_ANSWER, given=list(TEXTS), texts=TEXTS, issues=[], tokens=TOKENS, cost_usd=0.0, latency_s=0.0)
    assert out["g0_grounded"] == 1.0 and out["g2_subpart"] == 1 and out["g3_citation_recall"] == 1.0
    assert out["g1_quote"] == 0.0 and out["g4_checklist"] == 0.0 and out["failed"] is False


def test_score_line_without_answer_is_failed_with_zero_scores():
    out = score_line(CASE, None, given=list(TEXTS), texts=TEXTS, issues=["parse error: x"], tokens=TOKENS, cost_usd=0.01, latency_s=5.0)
    assert out["answer"] is None and out["failed"] is True
    assert out["g0_grounded"] == 0.0 and out["g1_quote"] == 0.0 and out["g2_subpart"] == 0
    assert out["g3_citation_recall"] == 0.0 and out["g4_checklist"] == 0.0
    assert out["g0_outside"] == [] and out["g1_mismatched"] == []
    assert out["issues"] == ["parse error: x"] and out["cost_usd"] == 0.01


# ---- SUU-275: run 기록 = 모양·채점기 버전·선별셋 여부. 심판 키 없음 ----


def _rows():
    return [
        {"case_id": "a", "g0_grounded": 1.0, "g1_quote": 1.0, "g2_subpart": 1, "g3_citation_recall": 1.0, "g4_checklist": 1.0,
         "failed": False, "cost_usd": 0.02, "latency_s": 40.0},
        {"case_id": "b", "g0_grounded": 0.5, "g1_quote": 0.0, "g2_subpart": 0, "g3_citation_recall": 0.0, "g4_checklist": 0.5,
         "failed": True, "cost_usd": 0.04, "latency_s": 60.0},
    ]


def test_answer_run_record_has_shape_subset_scorer_v2_and_no_judge():
    rec = answer_run_record("2026-09-26_answer_gates_gpt-5-mini_subset51", _rows(), search_run_id="2026-09-18_hybrid_v2_llm_gpt-5-mini",
                            model="gpt-5-mini", shape="gates", top_n=10, subset=True, cost=0.06,
                            tokens={"prompt_tokens": 50000, "completion_tokens": 10000})
    assert rec["run_id"] == "2026-09-26_answer_gates_gpt-5-mini_subset51"
    assert rec["search_run_id"] == "2026-09-18_hybrid_v2_llm_gpt-5-mini"
    assert rec["eval_set_version"] == "v2" and rec["subset"] is True and rec["n_cases"] == 2 and rec["top_n"] == 10
    assert rec["answer_model"] == "gpt-5-mini" and rec["shape"] == "gates" and rec["scorer_version"] == "v2"
    assert rec["always_sections"] == []
    assert rec["tokens"] == {"prompt": 50000, "completion": 10000, "prompt_per_case": 25000}
    assert rec["cost_usd"] == {"per_query": 0.03, "total": 0.06}
    assert rec["run_at"].endswith("Z")
    assert "judge_model" not in rec and "judge" not in rec["metrics"]


def test_answer_run_record_metrics_are_aggregate_v2():
    sys.path.insert(0, str(RAG.parent / "[2] db/pipeline/5_rag"))
    from ecfr_answer_score import aggregate_v2

    rec = answer_run_record("r", _rows(), search_run_id="s", model="m", shape="criteria", top_n=10, subset=False, cost=0.0,
                            always=("section-63.2", "section-63.7", "section-63.8"))
    assert rec["metrics"] == aggregate_v2(_rows())
    assert rec["metrics"]["g5_latency_s"] == 50.0 and rec["metrics"]["failed"] == ["b"]
    assert rec["always_sections"] == ["section-63.2", "section-63.7", "section-63.8"] and rec["subset"] is False


def test_v2_run_record_is_not_picked_by_the_v1_pass_line():
    # answer_pass_line.py(SUU-155)는 judge_model이 gpt-5-mini인 run만 기준 run으로 본다. v2 줄에 그 키가 없으니 옛 검사는 옛 run을 계속 본다
    from answer_pass_line import is_default_run

    rec = answer_run_record("r", _rows(), search_run_id="s", model="gpt-5-mini", shape="gates", top_n=10, subset=True, cost=0.0)
    assert is_default_run(rec) is False


def test_write_run_record_appends_or_replaces_line_with_same_run_id(tmp_path):
    path = tmp_path / "answer_runs.jsonl"
    path.write_text(json.dumps({"run_id": "old", "x": 1}) + "\n", encoding="utf-8")
    write_run_record(path, {"run_id": "new", "x": 2})
    write_run_record(path, {"run_id": "old", "x": 3})  # --replay로 다시 채점하면 같은 run_id 줄을 바꾼다
    runs = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert runs == [{"run_id": "old", "x": 3}, {"run_id": "new", "x": 2}]


# ---- SUU-275: 실제 run 2개(나열·관문)가 같은 51건으로 기록되어 있다 ----


def _saved_runs():
    return [json.loads(l) for l in ANSWER_RUNS.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_every_saved_answer_run_has_tokens():
    runs = _saved_runs()
    assert len(runs) >= 4
    for r in runs:
        assert r["tokens"]["prompt"] > 0 and r["tokens"]["completion"] > 0 and r["tokens"]["prompt_per_case"] > 0, r["run_id"]


def test_saved_criteria_and_gates_runs_share_the_same_51_cases():
    v2 = [r for r in _saved_runs() if r.get("scorer_version") == "v2"]
    by_shape = {r["shape"]: r for r in v2}
    assert {"criteria", "gates"} <= set(by_shape), "나열·관문 run이 한 줄씩 있어야 한다"
    subset = set(json.loads(SUBSET_PATH.read_text(encoding="utf-8"))["subset"])
    search_run_ids = set()
    for shape, rec in by_shape.items():
        assert rec["n_cases"] == 51 and rec["top_n"] == 10 and rec["subset"] is True and rec["answer_model"] == "gpt-5-mini", shape
        assert rec["always_sections"] == [] and "judge_model" not in rec and "judge" not in rec["metrics"], shape
        assert rec["metrics"]["n"] == 51 and rec["cost_usd"]["total"] > 0, shape
        search_run_ids.add(rec["search_run_id"])
        rows = [json.loads(l) for l in (RESULTS / f"{rec['run_id']}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        assert {r["case_id"] for r in rows} == subset, shape
        for row in rows:
            assert row["scorer_version"] == "v2" and "judge" not in row, row["case_id"]
            assert row["cost_usd"] > 0 and row["latency_s"] > 0, row["case_id"]
    assert len(search_run_ids) == 1  # 같은 검색 결과에서 출발
