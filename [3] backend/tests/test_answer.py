"""SUU-157: 질문 하나 → 검색(hybrid + 규칙 + LLM 리랭크) → 상위 10 조문 전문 → 판정 기준표 JSON. 외부 API는 전부 가짜.
SUU-166: 색인에 임베딩이 없다. 벡터 검색은 index.vector(pgvector RPC 가짜)가 한다."""
import json

from app.answer import CHUNK_TOP_K, TOP_N, answer_question
from app.index import Index
from ecfr_keyword import build_keyword_search

# 조문 12개(subpart PPPP 6개, subpart M 6개). 질문 "solvent welding"은 63.4481과 BM25로 맞는다. 임베딩은 없다(SUU-166)
SECTIONS = [(f"63.{4481 + i}", "PPPP") for i in range(6)] + [(f"63.{320 + i}", "M") for i in range(6)]
CHUNKS = [
    {
        "chunk_key": f"ecfr/40/63/subpart-{sp}/section-{sec}/0",
        "node_key": f"40/63/subpart-{sp}/section-{sec}",
        "context_text": f"section {sec} of subpart {sp}",
        "chunk_text": "solvent welding is coating" if sec == "63.4481" else f"body of {sec}",
    }
    for sec, sp in SECTIONS
]
# 63.4481은 조각이 하나 더 있다(/0-1). 조문 전문은 조각을 이어 붙인 것이어야 한다
CHUNKS.append({**CHUNKS[0], "chunk_key": "ecfr/40/63/subpart-PPPP/section-63.4481/0-1", "chunk_text": "(b) second piece"})

GOOD_ANSWER = json.dumps({
    "candidates": [{"subpart": "PPPP", "title": "Surface Coating of Plastic Parts",
                    "criteria": [{"criterion": "coats plastic parts", "citations": ["40 CFR 63.4481(a)"]}]}],
    "checklist": ["Is the facility a major source of HAP?"],
})


VECTOR_CALLS = []


def fake_vector(query_embedding, k):
    """pgvector RPC 흉내: 청크 순서대로 점수가 내려간다(63.4481 본문이 1등). 본문 붙은 청크에 score만 더한다"""
    VECTOR_CALLS.append((query_embedding, k))
    return [{**c, "score": 1.0 - i * 0.01} for i, c in enumerate(CHUNKS)][:k]


def make_index():
    VECTOR_CALLS.clear()
    return Index("rel-1", CHUNKS, build_keyword_search(CHUNKS), fake_vector)


def fake_apis(answer_text):
    calls = {"chat": []}

    def embed(request):
        assert request["texts"] == ["solvent welding"]
        return [1.0, 0.0]

    def rerank(question, chunks):
        return [1.0 if "solvent welding" in c["chunk_text"] else 0.5 for c in chunks]

    def llm(prompt):
        return {"text": "[1, 2, 3]", "prompt_tokens": 100, "completion_tokens": 10}

    def chat(request):
        calls["chat"].append(request)
        return {"text": answer_text, "prompt_tokens": 200, "completion_tokens": 20}

    return calls, dict(embed=embed, rerank=rerank, llm=llm, chat=chat)


def test_answer_question_returns_answer_ten_sections_tokens_cost_ms():
    assert TOP_N == 10 and CHUNK_TOP_K == 150
    calls, apis = fake_apis(GOOD_ANSWER)
    out = answer_question("solvent welding", index=make_index(), **apis)

    assert out["answer"]["candidates"][0]["subpart"] == "PPPP"
    assert out["answer"]["checklist"] == ["Is the facility a major source of HAP?"]
    assert len(out["sections"]) == 10
    assert out["sections"][0] == {"section_key": "section-63.4481", "subpart": "PPPP"}
    assert out["issues"] == []
    assert VECTOR_CALLS == [([1.0, 0.0], CHUNK_TOP_K)]  # 벡터 검색은 index.vector 한 번
    assert out["tokens"] == {"prompt": 300, "completion": 30}  # 리랭크 100+10, 답 200+20
    assert abs(out["cost_usd"] - (300 / 1e6 * 0.25 + 30 / 1e6 * 2.00)) < 1e-12  # gpt-5-mini 단가
    assert isinstance(out["ms"], int) and out["ms"] >= 0

    # 답 요청: gpt-5-mini, 조문 10개 전문(조각을 이어 붙임)이 들어간다
    assert len(calls["chat"]) == 1
    request = calls["chat"][0]
    assert request["model"] == "gpt-5-mini"
    user = request["messages"][-1]["content"]
    assert "SECTIONS (10)" in user
    assert "solvent welding is coating\n\n(b) second piece" in user


def test_broken_answer_json_gives_none_and_issue():
    _, apis = fake_apis("I cannot answer that.")
    out = answer_question("solvent welding", index=make_index(), **apis)

    assert out["answer"] is None
    assert len(out["issues"]) == 1 and "not JSON" in out["issues"][0]
    assert len(out["sections"]) == 10
    assert out["tokens"] == {"prompt": 300, "completion": 30}
