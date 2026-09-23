# SUU-78 fix(rag): 빈 청크를 색인 대상에서 거른다

## 목표
`select_subpart_chunks`가 반환하는 청크 중 `chunk_text`가 빈 문자열(공백만 포함)인 것을 걸러낸다.

## 건드릴 파일
- 고칠 것: `[2] db/pipeline/5_rag/ecfr_index_run.py`의 `select_subpart_chunks`
- 고칠 것: `[2] db/tests/5_rag/test_ecfr_index_run.py` — 이미 작성됨 (빨강 확인 완료)

## 안 하는 것
- `build_chunks`(SUU-70), `index_chunk`(SUU-75) 자체는 안 건드림 — 이 함수들이 빈 텍스트를 만들거나 처리하는 방식은 그대로 둔다
- `rank_chunks_by_similarity`는 이 티켓과 무관, 건드리지 않는다

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| `chunk_text`가 빈 문자열(공백만 포함)인 청크는 `select_subpart_chunks` 반환값에서 빠진다 | `test_select_subpart_chunks_drops_chunks_with_empty_chunk_text` |

## Codex 메모
- **왜 생기는가**: `build_chunks`(SUU-70)는 한 노드의 블록이 전부 `table` kind면, 기본(본문) 청크의 `block_nos`가 빈 리스트가 되고 표는 별도 자식 청크(`parent_chunk_key`가 채워진 것)로 분리한다. `select_subpart_chunks`가 `chunk_text`를 채울 때 `"\n\n".join(...)`을 빈 리스트에 하면 빈 문자열이 나온다. 실제 데이터 예: `40 CFR Part 63, Table 1 to Subpart XXXXXX`.
- **테스트 픽스처의 재현 사례**: `ecfr_part63_sample.xml`의 `subpart-XX` 안에 있는 `appendix-Table-1-to-Subpart-XX-of-Part-63` 노드가 블록이 전부 `table` kind라 실제로 빈 기본 청크를 만든다. `select_subpart_chunks(nodes, blocks, "40/63/subpart-XX")`로 재현 가능.
- **고칠 위치**: `select_subpart_chunks` 마지막에서 `chunk_text`를 채운 뒤 `return chunks` 직전에, `chunk["chunk_text"].strip()`이 참인 것만 남기고 반환하면 된다. (표 자식 청크는 `block_nos`가 항상 1개 이상이라 이 필터에 걸리지 않는다.)
- **실제 API로 재실행해 확인하는 일**(SUU-80에서 Part 63 전체 색인할 때 이 빈 청크들이 실제로 걸러지는지)은 이 티켓 범위 밖이다.
