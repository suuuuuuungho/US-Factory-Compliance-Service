"""SUU-158: FastAPI. POST /ask → answer_question 결과, GET /health → release_id, CORS는 FRONTEND_ORIGIN. 외부 연결은 전부 가짜."""
import importlib

import pytest
from fastapi.testclient import TestClient

from app.index import Index

FAKE_RESULT = {
    "answer": {"candidates": [{"subpart": "PPPP", "title": "t", "criteria": [{"criterion": "c", "citations": ["40 CFR 63.4481(a)"]}]}],
               "checklist": ["x"]},
    "sections": [{"section_key": "section-63.4481", "subpart": "PPPP"}],
    "issues": [], "tokens": {"prompt": 1, "completion": 1}, "cost_usd": 0.0, "ms": 1,
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://factory.vercel.app, http://localhost:3000")
    import app.main as main
    importlib.reload(main)  # FRONTEND_ORIGIN을 새로 읽는다
    # lifespan(Supabase 접속 + load_index)은 안 돌린다. TestClient를 with 없이 쓰면 startup이 안 돈다
    main.STATE["index"] = Index("rel-9", [], lambda q, k: [])
    asked = []

    def fake_answer_question(question, *, index, embed, rerank, llm, chat):
        asked.append((question, index.release_id))
        return FAKE_RESULT

    monkeypatch.setattr(main, "answer_question", fake_answer_question)
    c = TestClient(main.app)
    c.asked = asked
    return c


def test_post_ask_returns_answer_with_candidates(client):
    r = client.post("/ask", json={"question": "solvent welding plastic parts"})
    assert r.status_code == 200
    assert r.json()["answer"]["candidates"][0]["subpart"] == "PPPP"
    assert r.json()["sections"] == FAKE_RESULT["sections"]
    assert client.asked == [("solvent welding plastic parts", "rel-9")]  # 메모리 색인을 넘긴다


def test_blank_question_is_400(client):
    assert client.post("/ask", json={"question": "   "}).status_code == 400
    assert client.asked == []


def test_health_returns_release_id(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"release_id": "rel-9"}


def test_cors_preflight_allows_frontend_origin(client):
    headers = {"Origin": "https://factory.vercel.app", "Access-Control-Request-Method": "POST"}
    r = client.options("/ask", headers=headers)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "https://factory.vercel.app"
    # 목록에 없는 주소는 안 열린다
    r = client.options("/ask", headers={**headers, "Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers
