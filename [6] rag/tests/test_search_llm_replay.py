"""SUU-136: 저장된 gpt-5-mini 답을 검색 코드의 LLM 리랭크로 되돌리면 SUU-135 결과(0.692)와 같다."""
import json
import sys
from pathlib import Path

RAG = Path(__file__).parents[1]
sys.path[:0] = [str(RAG / "eval"), str(RAG.parent / "[2] db/pipeline/5_rag")]

from ecfr_llm_rerank import llm_rerank_sections  # noqa: E402
from llm_rerank import ruled_sections  # noqa: E402
from sweep_rules import score  # noqa: E402

HYBRID = RAG / "eval/results/2026-09-18_hybrid_v2.jsonl"
LLM = RAG / "eval/results/2026-09-18_hybrid_v2_llm_gpt-5-mini.jsonl"


def load(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_replay_saved_answers_matches_suu135():
    answers = {l["case_id"]: l["answer"] for l in load(LLM)}
    ndcg = []
    for line in load(HYBRID):
        ranked = llm_rerank_sections("", ruled_sections(line), lambda prompt: answers[line["case_id"]], texts={})
        ndcg.append(score(line["gold_sections"], [[s["section_key"], s["subpart"]] for s in ranked])["ndcg@10"])
    assert len(ndcg) == 102
    assert round(sum(ndcg) / len(ndcg), 3) == 0.692
