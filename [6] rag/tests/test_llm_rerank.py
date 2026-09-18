"""SUU-135: 저장된 hybrid+규칙 상위 20조문을 LLM으로 다시 줄 세우는 프롬프트·파싱·채점."""
import json
import sys
from pathlib import Path

RAG = Path(__file__).parents[1]
sys.path[:0] = [str(RAG / "eval"), str(RAG.parent / "[2] db/pipeline/5_rag")]

from llm_rerank import HEAD_CHARS, TOP_N, build_rerank_prompt, parse_ranking, rerank_line, top_sections  # noqa: E402
from sweep_rules import score  # noqa: E402

RESULT = RAG / "eval/results/2026-09-18_hybrid_v2.jsonl"


def test_prompt_has_question_and_truncated_sections():
    sections = [{"section_key": f"section-63.{i}", "subpart": "A", "text": "x" * 5000} for i in range(TOP_N)]
    prompt = build_rerank_prompt("Does Subpart A apply?", sections)
    assert "Does Subpart A apply?" in prompt
    assert all(f"section-63.{i}" in prompt for i in range(TOP_N))
    assert "x" * HEAD_CHARS in prompt and "x" * (HEAD_CHARS + 1) not in prompt


def test_parse_ranking_fills_missing_keys():
    keys = ["section-63.1", "section-63.2", "section-63.3", "section-63.4"]
    assert parse_ranking('```json\n["3", "1", "3", "9"]\n```', keys) == ["section-63.3", "section-63.1", "section-63.2", "section-63.4"]
    assert parse_ranking('["section-63.3", "section-63.1", "section-63.999"]', keys) == ["section-63.3", "section-63.1", "section-63.2", "section-63.4"]
    assert parse_ranking("garbage", keys) == keys


def test_identity_rerank_keeps_score():
    lines = [json.loads(l) for l in RESULT.read_text(encoding="utf-8").splitlines() if l.strip()]
    ndcg = []
    for line in lines:
        keys = [s["section_key"] for s in top_sections(line)]
        assert len(keys) == TOP_N
        out = rerank_line(line, lambda prompt: json.dumps(list(range(1, TOP_N + 1))), heads={})
        ndcg.append(score(line["gold_sections"], out["ranked_all"])["ndcg@10"])
    assert round(sum(ndcg) / len(ndcg), 3) == 0.631
