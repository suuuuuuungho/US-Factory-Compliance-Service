"""SUU-158: FastAPI. 켜질 때 색인 한 번(SUU-156), POST /ask → answer_question(SUU-157), GET /health → release_id.
SUU-159: /ask 한 번마다 rag_answer_log 한 줄.
SUU-167: 포트를 먼저 열고 색인은 스레드가 뒤에서 올린다. 준비 전엔 /health·/ask 503.
SUU-161: GET /section/{key} → 메모리 청크를 이어 붙인 조문 전문."""
from __future__ import annotations

import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ecfr_answer import call_openai_chat
from ecfr_chunk_index import call_isaacus_rerank_api, call_kanon2_api
from ecfr_eval import _subpart_of_chunk, section_key_of_chunk
from ecfr_llm_rerank import call_openai_rerank_api
from ecfr_search import build_rerank_request

from app.answer import answer_question, section_text
from app.index import load_index
from app.log import answer_log_row, save_answer_log

# 쉼표로 여러 개. 테스트는 이 모듈을 reload 해서 다시 읽는다
ORIGINS = [o.strip() for o in os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000").split(",") if o.strip()]
STATE: dict = {"index": None, "client": None}


def _load():
    from supabase import create_client
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    release_id = client.table("common_dataset_current").select("release_id").eq("dataset", "ecfr").execute().data[0]["release_id"]
    STATE["client"] = client
    STATE["index"] = load_index(client, release_id)  # 마지막에 넣는다. index가 차면 "준비됨"


@asynccontextmanager
async def lifespan(app):
    # Render는 포트가 열릴 때까지만 기다린다. 색인은 스레드에 맡기고 바로 연다
    threading.Thread(target=_load, daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"])


class Ask(BaseModel):
    question: str


@app.post("/ask")
def ask(body: Ask) -> dict:
    if STATE["index"] is None:
        raise HTTPException(503, "index not ready")
    if not body.question.strip():
        raise HTTPException(400, "question is empty")
    result = answer_question(
        body.question,
        index=STATE["index"],
        embed=call_kanon2_api,
        rerank=lambda q, chunks: call_isaacus_rerank_api(build_rerank_request(q, chunks))["scores"],
        llm=call_openai_rerank_api,
        chat=call_openai_chat,
    )
    if STATE.get("client"):  # 테스트(test_main.py)는 client가 없다 → 저장 건너뜀
        save_answer_log(STATE["client"], answer_log_row(body.question, result, STATE["index"].release_id))
    return result


@app.get("/section/{section_key}")
def section(section_key: str) -> dict:
    if STATE["index"] is None:
        raise HTTPException(503, "index not ready")
    index = STATE["index"]
    rows = [c for c in index.chunks if section_key_of_chunk(c) == section_key]  # 5,700개 선형 검색, ms 단위
    if not rows:
        raise HTTPException(404, "section not found")
    return {"section_key": section_key, "subpart": _subpart_of_chunk(rows[0]),
            "text": section_text(index, {"chunk_key": rows[0]["chunk_key"]})}


@app.get("/health")
def health():
    if STATE["index"] is None:
        return JSONResponse({"ready": False}, status_code=503)
    return {"release_id": STATE["index"].release_id}
