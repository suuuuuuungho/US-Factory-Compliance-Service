# SUU-76 feat(rag): Subpart XXXXXX를 실제로 색인해서 검색해본다

## 목표
Subpart 하나를 실제 Claude·Kanon 2 API로 색인해 `rag_chunk`에 넣고, 평가셋 질문으로 벡터 검색해서 정답 조문이 나오는지 확인한다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/5_rag/ecfr_index_run.py` — `select_subpart_chunks(nodes, blocks, subpart_key) -> list[dict]`, `rank_chunks_by_similarity(query_embedding, chunks, *, top_k=None) -> list[dict]`
- 만들 것: `[2] db/tests/5_rag/test_ecfr_index_run.py` — 이미 작성됨 (빨강 확인 완료)

## 안 하는 것
- **이 두 함수를 실제로 Subpart XXXXXX에 대해 실행하는 것** — Codex 범위 밖이다. `.env`의 실제 API 키로 Claude·Kanon 2를 부르고 `rag_chunk`에 진짜로 넣는 일, 컨텍스트 표본을 사람이 읽고 판단하는 일, 벡터 검색 결과를 확인하는 일, Artifact를 만드는 일은 **이 티켓의 진짜 완료 기준이지만 Claude(또는 사람)가 merge 후 직접 실행해서 확인한다.** Codex는 아래 두 순수 함수만 테스트를 통과하게 구현하면 된다.
- 리랭킹·하이브리드(BM25) 검색 결합 — 벡터 검색 단독만
- Part 63 전체 색인 (이 티켓은 Subpart 하나만)
- pgvector HNSW 인덱스를 실제로 쓰는 SQL 유사도 검색(RPC 등) — 이 티켓 규모(Subpart 하나, 청크 수십 개)에서는 Python에서 코사인 유사도를 직접 계산하는 것으로 충분하다. Postgres 쪽 벡터 검색 함수는 범위 밖.

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 (Codex가 통과시킬 부분) |
|---|---|
| Subpart 청크만 정확히 뽑히고, 표(table) 분리·중첩된 subject_group까지 포함한다 | `test_select_subpart_chunks_only_includes_that_subparts_chunks`, `test_select_subpart_chunks_includes_nested_subject_group_sections` |
| 각 청크의 `chunk_text`가 그 청크에 속한 block들의 `text_content`를 순서대로 이어붙인 것과 같다 | `test_select_subpart_chunks_fills_chunk_text_from_block_text_content` |
| 쿼리 임베딩과 코사인 유사도가 높은 청크가 먼저 온다 | `test_ranks_chunks_by_cosine_similarity_descending` |
| `top_k`를 주면 그 개수만큼만 반환한다 | `test_rank_chunks_top_k_limits_result_count` |

**아래는 테스트로 확인하지 않는, 사람(Claude)이 merge 후 직접 실행해서 확인할 진짜 완료 기준이다** (Linear 티켓 원문 그대로):
- [ ] Subpart XXXXXX의 청크가 모두 `rag_chunk`에 실제로 들어간다 (context_text, embedding 채워짐)
- [ ] 컨텍스트 표본 3개를 사람이 읽었을 때 다른 Subpart 얘기나 적용 판단이 섞여있지 않다
- [ ] `dashboard-vicor-2020-04-16` 질문을 벡터 검색했을 때 `40 CFR 63.11514(a)` 조문이 상위 결과에 나온다
- [ ] 청크 원문·컨텍스트·검색 결과를 Artifact로 정리해서 보여준다

## Codex 메모
- **`select_subpart_chunks`**: `ecfr_chunks.build_chunks(nodes, blocks)` (SUU-70)를 그대로 쓰되, 먼저 `node_key`가 `f"{subpart_key}/"`로 시작하는 노드만 걸러서 넘긴다. subpart 자기 자신(`node_key == subpart_key`, 슬래시 없음)은 청크 대상이 아니므로 `startswith(prefix)`(끝에 `/` 포함)로 걸러야 정확하다. `subpart-J`처럼 `subject_group`이 중간에 끼는 구조도 있는데, prefix 방식이면 깊이 상관없이 자동으로 포함된다.
- **`chunk_text` 채우기**: `build_chunks`가 반환하는 청크에는 `block_nos`만 있고 텍스트가 없다. `node_key`별로 `{block_no: text_content}` 맵을 만들어서, 청크의 `block_nos` 순서대로 `text_content`를 뽑아 `"\n\n"`으로 이어붙여 `chunk["chunk_text"]`에 채운다.
- **`rank_chunks_by_similarity`**: 순수 함수, DB/네트워크 없음. 코사인 유사도 = `dot(a,b) / (norm(a) * norm(b))`. `chunks`의 각 dict는 최소한 `"embedding"` 키를 가진다고 가정한다. 반환값은 원본 dict를 복사해 `"score"` 키를 추가한 새 dict 리스트, `score` 내림차순 정렬. `top_k`를 주면 앞에서부터 그만큼만 자른다.
- **실제 실행 스크립트(`__main__`)**: 이 티켓에서 Codex가 작성할 필요 없다(테스트가 없으므로). 다만 짜두면 Claude가 merge 후 그대로 쓸 수 있으니, 참고로 실행 흐름은 이렇다 — `select_subpart_chunks`로 청크 목록 확보 → 각 청크에 대해 `ecfr_chunk_index.index_chunk(node, chunk, doc_text, client=client)`(SUU-75, 기본값이 실제 API 호출) 반복 호출 → `rag_chunk`에서 그 release의 임베딩을 다시 읽어와 `rank_chunks_by_similarity`로 질문과 비교. `doc_text`(Claude 캐싱용 전체 문서 텍스트)는 그 subpart의 모든 청크 `chunk_text`를 이어붙이면 된다.
- **의존 관계**: SUU-75(`index_chunk`)가 merge되어야 Claude가 실제 실행을 할 수 있다. 이 스펙(테스트 2개 함수)은 SUU-75와 무관하게 지금 바로 구현 가능하다.
