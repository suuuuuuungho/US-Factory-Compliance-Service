# SUU-85 fix(rag): 표 청크에 상위 제목을 붙여 색인한다

## 목표
`select_subpart_chunks`가 청크를 만들 때, 실제 내용(본문/표)이 있는 청크에 한해 그 노드의 제목(`heading`)을 `chunk_text` 맨 앞에 붙인다.

## 건드릴 파일
- 고칠 것: `[2] db/pipeline/5_rag/ecfr_index_run.py`의 `select_subpart_chunks`
- 고칠 것: `[2] db/tests/5_rag/test_ecfr_index_run.py` — 이미 작성됨 (빨강 확인 완료: 3 failed, 3 passed)

## 안 하는 것
- `build_chunks`(SUU-70)의 청크 분리 로직 자체는 안 건드림
- 표 파싱(`ecfr_blocks.py`, SUU-83)은 안 건드림
- `rank_chunks_by_similarity`는 이 티켓과 무관

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 표만 있는 노드의 표 자식 청크는 `chunk_text`가 그 노드의 `heading` + 빈 줄로 시작하고, 그 뒤에 표 내용이 있다 | `test_select_subpart_chunks_prefixes_table_chunk_with_node_heading` |
| 본문 블록이 전혀 없는 노드의 기본 청크는 여전히 결과에서 빠진다(제목만 붙어서 살아나면 안 됨) | `test_select_subpart_chunks_drops_chunks_with_empty_chunk_text` (기존, 계속 통과해야 함) |
| 본문이 있는 일반 섹션 청크도 제목이 앞에 붙는다(회귀 없음) | `test_select_subpart_chunks_prefixes_body_chunk_with_node_heading` |
| 본문 청크의 `chunk_text` = `heading` + `"\n\n"` + 블록 텍스트를 `"\n\n"`으로 이은 것 | `test_select_subpart_chunks_fills_chunk_text_from_block_text_content` (기존 테스트를 새 기대값으로 고침) |

## Codex 메모
- **순서가 중요하다**: 지금 코드는 `chunk_text`를 채운 뒤 `[chunk for chunk in chunks if chunk["chunk_text"].strip()]`로 빈 것을 거른다(SUU-78). 제목 붙이기는 **이 필터링 다음에** 해야 한다. 필터링 전에 붙이면, 본문 블록이 하나도 없는 기본 청크(표만 있는 노드의 경우)도 "제목만 있는" 비어있지 않은 문자열이 되어 필터를 통과해버려 SUU-78이 고친 버그가 재발한다.
- **구현 힌트**: `nodes` 리스트로 `node_key -> heading` 딕셔너리를 만들고, 필터링 후 남은 각 청크에 대해 `chunk["chunk_text"] = f"{node_heading_by_key[chunk['node_key']]}\n\n{chunk['chunk_text']}"`처럼 적용한다.
- **왜 필요한가**: 표만 있는 노드(예: `appendix-Table-1-to-Subpart-XX-of-Part-63`)는 `HEAD` 태그가 `parse_blocks`(`ecfr_blocks.py`)에서 통째로 버려져서, 표 청크의 `chunk_text`에는 "Region | Address | State ..." 같은 표 내용만 있고 이게 무슨 표인지 알려주는 제목이 없다.
- **테스트 픽스처**: 기존 `test_ecfr_index_run.py`에 있는 표 노드 픽스처를 그대로 쓰되, 그 노드의 `heading` 값을 확인하고 `chunk_text.startswith(heading)`을 검증하면 된다.
