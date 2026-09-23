# SUU-92 feat(rag): 질문 하나로 관련 조문 상위 k개를 돌려준다

## 목표
질문 문장 → 관련 조문(section) 상위 k개를 돌려주는 `search_sections`를 제품 코드에 만들고, 평가 스크립트가 그것을 쓰게 한다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/5_rag/ecfr_search.py`
- 고칠 것: `[6] rag/eval/run_eval.py` — 질문 임베딩·검색 부분을 `search_sections` 호출로 바꾼다 (결과 파일 형식·캐시 동작은 그대로)
- 테스트(이미 있음, 수정 금지): `[2] db/tests/5_rag/test_ecfr_search.py`

## 안 하는 것
- DB HNSW(`<=>`) 검색, hybrid(BM25), 리랭커, API 엔드포인트, 답변 생성
- `ecfr_eval.py`, `ecfr_index_run.py`, `ecfr_embed.py` 수정
- 평가 재실행·결과 파일 갱신 (Claude가 머지 후 함)
- `tests/` 아래 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 질문을 `task="retrieval/query"` 요청으로 `embed`에 넘긴다 | `test_search_sections_embeds_question_with_query_task` |
| 결과는 조문 단위, `{"section_key","chunk_key","subpart","score"}` 모양, 점수 내림차순 | `test_search_sections_returns_sections_sorted_by_score` |
| 같은 조문의 청크는 하나로 접히고 최고 점수 청크가 남는다 | `test_search_sections_collapses_same_section_and_keeps_best_chunk` |
| `top_k`개까지만 | `test_search_sections_cuts_at_top_k` |
| 청크가 없으면 빈 목록 | `test_search_sections_with_no_chunks_returns_empty` |
| `run_eval.py`를 바꿔 재실행해도 `2026-09-17_contextual_v1`과 케이스별 `returned_sections`가 같다 | (Claude가 머지 후 실제 실행으로 확인) |

## Codex 메모
- 시그니처: `search_sections(question: str, *, embed, chunks, top_k: int = 5, chunk_top_k: int = 300) -> list[dict]`
  - `embed(request: dict) -> list[float]` — 질문 임베딩 호출. 요청은 `ecfr_eval.build_query_embedding_request(question)`으로 만든다. 실제 실행에서는 `ecfr_chunk_index.call_kanon2_api`를 넘긴다
  - `chunks` — `{"chunk_key", "node_key", "embedding"}`를 가진 dict 목록(`rag_chunk` 행). DB 조회는 함수 밖에서 한다
  - 흐름: `rank_chunks_by_similarity(query_embedding, chunks, top_k=chunk_top_k)` → `ecfr_eval.rank_sections(ranked, k_max=top_k)`. 새 계산 로직을 쓰지 말고 이 둘을 그대로 조합한다
  - `chunk_top_k`는 조문 `top_k`개를 채우기 위한 청크 후보 수(한 조문에 청크가 여럿이므로 `top_k`보다 커야 한다). 기본 300은 `run_eval.py`의 `CHUNK_TOP_K`와 같다
- `run_eval.py` 수정 범위: 케이스 루프 안의 `rank_chunks_by_similarity` + `rank_sections` 두 줄을 `search_sections(c["question"], embed=lambda r: cache[...]["embedding"], chunks=chunks, top_k=K_MAX)` 형태로 바꾼다. 질문 임베딩 캐시(`query_embeddings.json`)는 그대로 두고, `embed`에 "캐시에서 꺼내는 함수"를 넘기면 된다. `search_ms` 측정 위치·결과 필드는 바꾸지 않는다
- 표준 라이브러리만. `sys.path` 설정은 `run_eval.py`에 이미 있다(`[2] db/pipeline/5_rag`)
