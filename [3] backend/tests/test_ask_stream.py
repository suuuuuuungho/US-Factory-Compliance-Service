"""SUU-178: POST /ask/stream → SSE. event: stage ×3 (search/found/answer) → event: result (기존 /ask JSON) 또는 event: error.
answer_question은 가짜(SUU-177의 on_event를 3번 부른다). 외부 연결 없음."""
import importlib
import json

import pytest
from fastapi.testclient import TestClient

from app.index import Index

from tests.test_main import FAKE_RESULT

STAGES = [
    {"stage": "search"},
    {"stage": "found", "sections": FAKE_RESULT["sections"]},
    {"stage": "answer"},
]


def parse_sse(text: str) -> list[tuple[str, dict]]:
    """'event: x\ndata: {...}\n\n' 덩어리들 → [(event, data), ...]"""
    out = []
    for block in text.strip().split("\n\n"):
        event, data = None, None
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
        out.append((event, data))
    return out


@pytest.fixture
def make_client(monkeypatch):
    import app.main as main
    importlib.reload(main)
    main.STATE["index"] = Index("rel-9", [], lambda q, k: [])
    main.STATE["client"] = None

    def _make(fail: Exception | None = None):
        def fake_answer_question(question, *, index, embed, rerank, llm, chat, on_event=None):
            for e in STAGES:
                on_event(e)
                if fail and e["stage"] == "answer":
                    raise fail
            return FAKE_RESULT

        monkeypatch.setattr(main, "answer_question", fake_answer_question)
        return TestClient(main.app)

    return _make


def test_stream_sends_three_stages_then_result(make_client):
    r = make_client().post("/ask/stream", json={"question": "solvent welding"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(r.text)
    assert [e for e, _ in events] == ["stage", "stage", "stage", "result"]
    assert [d for _, d in events[:3]] == STAGES


def test_result_data_matches_ask_response(make_client):
    r = make_client().post("/ask/stream", json={"question": "solvent welding"})
    _, result = parse_sse(r.text)[-1]
    assert result == FAKE_RESULT
    assert set(result) == {"answer", "sections", "issues", "tokens", "cost_usd", "ms"}


def test_error_during_answer_becomes_error_event(make_client):
    r = make_client(fail=RuntimeError("openai down")).post("/ask/stream", json={"question": "solvent welding"})
    assert r.status_code == 200  # 헤더는 이미 나갔다. 에러는 이벤트로
    events = parse_sse(r.text)
    assert [e for e, _ in events] == ["stage", "stage", "stage", "error"]
    assert "openai down" in events[-1][1]["detail"]


def test_not_ready_is_503_and_blank_question_is_400(make_client):
    import app.main as main
    c = make_client()
    assert c.post("/ask/stream", json={"question": "   "}).status_code == 400
    main.STATE["index"] = None
    assert c.post("/ask/stream", json={"question": "solvent welding"}).status_code == 503
