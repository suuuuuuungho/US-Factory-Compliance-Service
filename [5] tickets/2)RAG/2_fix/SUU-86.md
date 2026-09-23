# SUU-86 fix(rag): 색인 시 조문 제목 대신 Subpart 이름을 넘긴다

## 목표
`index_chunk`가 컨텍스트 프롬프트에 넣는 Subpart 이름을 호출자가 `subpart_name`으로 명시하게 하고, 청크의 `node_key`로 그 Subpart 노드의 `heading`을 찾아주는 도우미 `subpart_heading_for`를 만든다.

## 건드릴 파일
- 고칠 것: `[2] db/pipeline/5_rag/ecfr_chunk_index.py`의 `index_chunk` — `subpart_name: str | None`을 **기본값 없는 키워드 전용 인자**로 추가하고 `build_context_request(..., subpart_name=subpart_name)`으로 그대로 넘긴다. `node["heading"]`을 `subpart_name` 자리에 쓰는 코드는 없앤다
- 만들 것: `[2] db/pipeline/5_rag/ecfr_index_run.py`에 `subpart_heading_for(nodes, node_key) -> str` — `__all__`에도 추가
- 고칠 것: `[2] db/tests/5_rag/test_ecfr_chunk_index.py`, `[2] db/tests/5_rag/test_ecfr_index_run.py` — 이미 작성됨 (빨강 확인 완료)

## 안 하는 것
- `build_context_request`(`ecfr_context.py`, SUU-82)는 안 건드림 — 이미 `subpart_name`을 올바르게 처리한다
- `select_subpart_chunks`, `rank_chunks_by_similarity`는 안 건드림
- 이미 색인된 청크 재색인은 SUU-80에서 (스크래치패드 실행 스크립트는 저장소에 없으므로 이 티켓 범위 밖)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| `index_chunk(subpart_name=X)`로 부르면 Claude 요청 프롬프트에 `This chunk belongs to X.`가 있고, 조문 노드 `heading`은 그 자리에 없다 | `test_index_chunk_uses_given_subpart_name_not_section_heading` |
| `subpart_name=None`이면 프롬프트에 `This chunk belongs to` 줄이 없다 | `test_index_chunk_with_none_subpart_name_omits_belongs_line` |
| `subpart_name`을 빠뜨리면 `TypeError` (다시는 조용히 잘못된 값이 들어가지 않게) | `test_index_chunk_requires_subpart_name_keyword` |
| 기존 동작(호출 순서, 저장 행) 회귀 없음 | `test_calls_claude_then_kanon2_with_context_chained_into_embedding_request`, `test_saved_row_has_context_embedding_hash_and_embedded_status` (기존, `subpart_name` 인자만 추가됨) |
| `subpart_heading_for(nodes, node_key)`는 `node_key`가 속한 Subpart 노드(`node_type='subpart'`)의 `heading`을 돌려준다. 조문 자신의 `heading`이 아니고, 서로 다른 Subpart는 다른 값 | `test_subpart_heading_for_returns_subpart_node_heading_not_section_heading` |

## Codex 메모
- **왜 생겼나**: SUU-82(PR #58)가 `build_context_request`에 `subpart_name`을 추가했지만, 호출부 `ecfr_chunk_index.py:53`이 `subpart_name=node["heading"]`을 넘겼다. 이 `node`는 청크가 속한 **조문(section) 노드**라서 heading이 `"§ 63.7342 What records must I keep?"` 같은 조문 제목이지 Subpart 이름이 아니다. 실제 955개 재색인에서 여전히 `"Subpart RRR"` 같은 가짜 이름이 나왔다. 상세: `[6] rag/색인 문제 해결.md` 1번.
- **`index_chunk` 시그니처**: `def index_chunk(node, chunk, doc_text, *, subpart_name: str | None, client, call_claude=..., call_kanon2=...)` — `subpart_name`에 기본값을 주지 않는다. 테스트가 빠뜨렸을 때 `TypeError`를 기대한다.
- **`subpart_heading_for` 구현 힌트**: `node_key`는 `40/63/subpart-CCCCC/section-63.7342` 또는 `40/63/subpart-XX/subject-group-.../section-63.1097` 모양이다. 앞 3조각(`"/".join(node_key.split("/")[:3])`)이 Subpart 키(`40/63/subpart-CCCCC`)다. `nodes`에서 `node_type == "subpart"`이고 `node_key`가 그 값인 노드의 `heading`을 돌려준다. 못 찾으면 `KeyError`를 내도 된다(조용히 None 반환하지 않는다).
- **픽스처**: `test_ecfr_index_run.py`의 `parsed_nodes_and_blocks`가 만드는 nodes에는 `40/63/subpart-G`(heading `"Subpart G—National Emission Standards..."`), `40/63/subpart-XX`(heading `"Subpart XX—National Emission Standards for Ethylene..."`) subpart 노드가 있다.
- **실행 스크립트를 다시 짤 때(SUU-80, Claude 담당)**: `index_chunk(node, chunk, doc_text, subpart_name=subpart_heading_for(nodes, chunk["node_key"]), client=client)`처럼 부른다.
