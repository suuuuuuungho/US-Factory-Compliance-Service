"""SUU-158: FastAPI. 켜질 때 색인 한 번(SUU-156), POST /ask → answer_question(SUU-157), GET /health → release_id."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ecfr_answer import call_openai_chat
from ecfr_chunk_index import call_isaacus_rerank_api, call_kanon2_api
from ecfr_llm_rerank import call_openai_rerank_api
from ecfr_search import build_rerank_request

from app.answer import answer_question
from app.index import load_index

# 쉼표로 여러 개. 테스트는 이 모듈을 reload 해서 다시 읽는다
ORIGINS = [o.strip() for o in os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000").split(",") if o.strip()]
STATE: dict = {"index": None}


@asynccontextmanager
async def lifespan(app):
    from supabase import create_client
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    release_id = client.table("common_dataset_current").select("release_id").eq("dataset", "ecfr").execute().data[0]["release_id"]
    STATE["index"] = load_index(client, release_id)
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"])


class Ask(BaseModel):
    question: str


@app.post("/ask")
def ask(body: Ask) -> dict:
    if not body.question.strip():
        raise HTTPException(400, "question is empty")
    return answer_question(
        body.question,
        index=STATE["index"],
        embed=call_kanon2_api,
        rerank=lambda q, chunks: call_isaacus_rerank_api(build_rerank_request(q, chunks))["scores"],
        llm=call_openai_rerank_api,
        chat=call_openai_chat,
    )


@app.get("/health")
def health() -> dict:
    return {"release_id": STATE["index"].release_id}
