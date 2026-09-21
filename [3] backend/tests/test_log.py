"""SUU-159: 질문 한 번 = rag_answer_log 한 줄. 행 만들기(log.py), /ask 뒤 insert 한 번, insert가 깨져도 응답은 그대로."""
import importlib
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.index import Index
from app.log import answer_log_row

MIGRATION = Path(__file__).parents[2] / "[2] db" / "migrations" / "SUU-159_rag_answer_log.sql"

RESULT = {
    "answer": {"candidates": [{"subpart": "PPPP", "title": "t", "criteria": [{"criterion": "c", "citations": ["40 CFR 63.4481(a)"]}]}],
               "checklist": ["x"]},
    "sections": [{"section_key": "section-63.4481", "subpart": "PPPP"}],
    "issues": ["citation outside given sections: section-63.2 (40 CFR 63.2)"],
    "tokens": {"prompt": 27000, "completion": 5000},
    "cost_usd": 0.01675,
    "ms": 12345,
}


def test_answer_log_row_fills_every_column():
    row = answer_log_row("solvent welding", RESULT, "rel-9")
    assert row == {
        "release_id": "rel-9",
        "question": "solvent welding",
        "answer": RESULT["answer"],
        "sections": RESULT["sections"],
        "issues": RESULT["issues"],
        "prompt_tokens": 27000,
        "completion_tokens": 5000,
        "cost_usd": 0.01675,
        "ms": 12345,
    }
    # 답이 깨진 경우 answer는 null로 남는다
    assert answer_log_row("q", {**RESULT, "answer": None}, "rel-9")["answer"] is None


def test_migration_creates_rag_answer_log_with_rls():
    sql = " ".join(MIGRATION.read_text(encoding="utf-8").split()).lower()
    assert "create table rag_answer_log (" in sql
    for column in ("id", "created_at", "release_id", "question", "answer", "sections", "issues",
                   "prompt_tokens", "completion_tokens", "cost_usd", "ms"):
        assert re.search(rf"[\(,]\s*{column} ", sql), column
    assert "alter table rag_answer_log enable row level security" in sql


class FakeSupabase:
    def __init__(self, fail=False):
        self.fail, self.inserted = fail, []

    def table(self, name):
        assert name == "rag_answer_log"
        return self

    def insert(self, row):
        self._row = row
        return self

    def execute(self):
        if self.fail:
            raise RuntimeError("db down")
        self.inserted.append(self._row)
        return self


@pytest.fixture
def make_client(monkeypatch):
    import app.main as main
    importlib.reload(main)
    main.STATE["index"] = Index("rel-9", [], lambda q, k: [])
    monkeypatch.setattr(main, "answer_question", lambda question, **_: RESULT)

    def make(db):
        main.STATE["client"] = db
        return TestClient(main.app)

    return make


def test_ask_inserts_one_log_row(make_client):
    db = FakeSupabase()
    r = make_client(db).post("/ask", json={"question": "solvent welding"})
    assert r.status_code == 200 and r.json() == RESULT
    assert db.inserted == [answer_log_row("solvent welding", RESULT, "rel-9")]


def test_ask_still_answers_when_insert_fails(make_client):
    r = make_client(FakeSupabase(fail=True)).post("/ask", json={"question": "solvent welding"})
    assert r.status_code == 200 and r.json() == RESULT
