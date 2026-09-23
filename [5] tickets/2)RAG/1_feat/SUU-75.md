# SUU-75 feat(rag): 청크 하나를 실제로 색인해 rag_chunk에 적재

## 목표
청크 하나를 Claude(컨텍스트)·Kanon 2(임베딩) API로 실제로 색인해 `rag_chunk` 한 행에 저장한다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/5_rag/ecfr_chunk_index.py` — `index_chunk(node, chunk, doc_text, *, client, call_claude=..., call_kanon2=...) -> None`, `call_claude_api(request) -> str`, `call_kanon2_api(request) -> list[float]`
- 만들 것: `[2] db/tests/5_rag/test_ecfr_chunk_index.py` — 이미 작성됨 (빨강 확인 완료)
- 고칠 것: `requirements.txt` — `anthropic` 추가 (call_claude_api가 씀). `requests`는 이미 환경에 있지만 명시적으로 추가해도 됨.

## 안 하는 것
- 여러 청크 반복 처리 (다음 POC 티켓 SUU-76 범위)
- 실패 재시도
- 실제 API 키로 진짜 호출해보는 것 — 이 티켓은 가짜 함수 주입 테스트만 통과하면 된다. 사람이 SUU-76에서 직접 실행한다.
- `tsv` 컬럼 채우기 (범위 밖, 검색 티켓에서 다룸)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| `call_claude`로 컨텍스트를 받고, `call_kanon2`로 그 컨텍스트+청크를 임베딩한 뒤, 순서·인자가 올바르다 | `test_calls_claude_then_kanon2_with_context_chained_into_embedding_request` |
| `rag_chunk`에 upsert된 행에 `context_text`, `embedding`, `content_hash`, `index_status="embedded"`가 채워진다 | `test_saved_row_has_context_embedding_hash_and_embedded_status` |
| 기본값은 실제 Claude/Kanon 2 호출 함수다 | `test_uses_the_real_api_callers_by_default` |

## Codex 메모
- **기존 조립 함수를 그대로 쓴다**: `ecfr_context.build_context_request(doc_text, chunk_text)` (SUU-71), `ecfr_embed.build_embedding_request(context_text, chunk_text)` (SUU-73). `index_chunk`는 이 둘을 호출하고 그 사이·이후에 실제 API 호출(`call_claude`, `call_kanon2`)을 끼워 넣는 얇은 조립 함수다.
- **`call_claude(request) -> str` 계약**: `request`는 `build_context_request`가 반환한 dict 그대로(`system`, `messages`, `prompt_version`). 반환값은 컨텍스트 텍스트 문자열 그 자체(파싱 이미 끝난 상태) — `index_chunk`는 문자열만 다룬다.
- **`call_kanon2(request) -> list[float]` 계약**: `request`는 `build_embedding_request`가 반환한 dict(`texts`는 원소 1개). 반환값은 그 한 텍스트의 임베딩 벡터(길이 1792) 그 자체 — 리스트를 다시 벗기는 일은 `call_kanon2` 안에서 끝낸다.
- **`call_claude_api` 실제 구현**: `anthropic` 패키지(`Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])`), 모델은 `claude-haiku-4-5` (RAG 계획 문서 [4]절). `client.messages.create(model=..., max_tokens=..., system=request["system"], messages=request["messages"])` 호출 후 `response.content[0].text` 반환.
- **`call_kanon2_api` 실제 구현**: Isaacus `POST https://api.isaacus.com/v1/embeddings`, 헤더 `Authorization: Bearer {ISAACUS_API_KEY}`, 바디는 `{"model": "kanon-2-embedder", **request}` (RAG 계획 문서 [5]절, [2] db/pipeline/5_rag/ecfr_embed.py의 request 모양 그대로 사용). 응답에서 첫 번째 임베딩 벡터를 꺼내 반환한다(정확한 응답 필드명은 Isaacus API 문서 참고 — 이 티켓에서 실제로 호출해보지 않으므로 필드명이 다르면 SUU-76 실행 때 사람이 잡는다).
- **환경변수**: `ANTHROPIC_API_KEY`, `ISAACUS_API_KEY`. 기존 `.env` 파일에 추가해야 한다(코드에는 안 넣음).
- **`node`/`chunk` 모양**: `node`는 `ecfr_node` 행 모양(특히 `release_id`, `node_key`가 필요). `chunk`는 `rag_chunk`에 저장할 필드를 이미 다 가진 dict(`chunk_key`, `dataset`, `doc_key`, `node_key`, `block_from`, `block_to`, `hierarchy_path`, `heading`, `citation`, `source_locator`, `chunk_text`) — 이 dict를 어떻게 조립하는지는 이 티켓 범위 밖(호출하는 쪽, 즉 SUU-76에서 준비한다).
- **`content_hash`**: `sha256(chunk_text + "\n\n" + context_text)`의 hex digest. 재색인 시 내용이 같으면 같은 해시가 나오게 하기 위함(나중 티켓에서 "바뀐 것만 재색인"에 쓸 수 있음, 이 티켓에서는 그냥 채우기만 한다).
- **upsert**: `client.table("rag_chunk").upsert([row], on_conflict="release_id,chunk_key").execute()` — SUU-74에서 만든 PK 그대로.
