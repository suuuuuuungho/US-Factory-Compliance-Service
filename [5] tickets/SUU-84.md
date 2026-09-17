# SUU-84 fix(rag): 너무 큰 조문만 쪼개 임베딩 실패를 막는다

## 목표
`build_chunks`가 본문 청크 글자 수가 임계값(`MAX_CHUNK_CHARS = 30_000`)을 넘을 때만 `label_path` 문단 경계로 여러 조각으로 나눈다. 임계값 이하는 지금과 100% 같은 출력.

## 건드릴 파일
- 고칠 것: `[2] db/pipeline/5_rag/ecfr_chunks.py` — `MAX_CHUNK_CHARS` 상수 추가, `build_chunks(nodes, blocks, *, max_chars=MAX_CHUNK_CHARS)`로 키워드 인자 추가, 본문 청크 쪼개기
- 고칠 것: `[2] db/tests/5_rag/test_ecfr_chunks.py` — 이미 작성됨 (빨강 확인 완료: 7 failed, 5 passed)

## 안 하는 것
- 표(`kind == "table"`) 청크는 쪼개지 않는다 — 지금처럼 블록 하나 = 청크 하나(`/1`, `/2`…)
- `select_subpart_chunks`, `index_chunk`, `ecfr_embed.py`(`overflow_strategy`)는 안 건드림
- 블록 하나를 글자 단위로 자르는 것 (블록은 최소 단위)
- Part 63 재적재(SUU-87), 재색인(SUU-80)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 임계값 상수 `MAX_CHUNK_CHARS == 30_000`이 `ecfr_chunks`에 있다 | `test_max_chunk_chars_constant_is_thirty_thousand` |
| 임계값 넘는 조문은 `label_path[0]` 경계로 나뉘고, 조각 키는 `/0`, `/0-1`, `/0-2`…, 각 조각이 임계값 안 | `test_section_over_limit_is_split_at_top_level_label_boundaries` |
| 1단계 조각이 여전히 크면 `label_path[1]`로 다시 나눈다. 상위 문단 본문 블록은 첫 하위 조각에 | `test_recurses_to_deeper_label_level_when_top_level_group_is_still_too_large` |
| `label_path`가 짧은(빈) 블록은 바로 앞 조각에 붙고, 맨 앞이면 첫 조각에. `block_no` 순서 유지 | `test_leading_unlabeled_blocks_go_to_first_piece_and_block_order_is_kept` |
| 블록 하나가 임계값을 넘어도 그 블록은 통째로 한 조각(자르지 않음) | `test_single_block_over_limit_is_kept_whole_not_truncated` |
| 임계값 이하 조문은 청크 1개, 키 `/0`, 기본값 호출과 명시 호출 결과 동일 | `test_section_within_limit_is_unchanged_single_chunk` |
| 쪼개진 조문의 표 청크는 키 `/1`…, `parent_chunk_key`는 `/0` 그대로 | `test_table_chunks_of_split_section_still_point_to_first_piece` |
| 픽스처 XML(큰 조문 없음)은 기본값으로 돌렸을 때 `-`가 붙은 키가 하나도 없다 (회귀 없음) | `test_fixture_sections_are_all_under_default_limit_so_output_is_unchanged`, 기존 4개 |

## Codex 메모
- **글자 수 기준**: `len("\n\n".join(block["text_content"] for block in 조각))` — `select_subpart_chunks`가 `chunk_text`를 만드는 방식과 같다. 테스트 `_chunk_len`이 이 기준으로 검사한다.
- **입력 형태**: `blocks` 원소는 `node_key`, `block_no`, `kind`, `text_content`, `label_path`(문자열 리스트, 예 `["a", "1", "i"]`, 앞머리 문단은 `[]`)를 가진 dict. `label_path`는 `ecfr_labels.assign_label_paths`가 채운다. heading/note 같은 비문단 블록은 앞 문단의 `label_path`를 그대로 상속한다.
- **묶기 규칙(깊이 `d`)**: 본문 블록을 `block_no` 순으로 보며 `label_path[d]`가 같은 연속 블록을 한 묶음으로 만든다. `len(label_path) <= d`인 블록(그 깊이 라벨 없음)은 **현재 묶음에 그대로 붙인다**(묶음이 아직 없으면 첫 묶음 시작). 라벨이 바뀌면 새 묶음.
- **재귀**: 묶음 하나가 여전히 `max_chars`를 넘으면 그 묶음을 깊이 `d+1`로 다시 묶는다. 더 나눌 수 없으면(묶음이 1개만 나오거나 블록이 1개) 그대로 둔다. 자연스럽게 "블록 하나가 임계값 초과 → 통째로"가 된다.
- **묶음끼리 합치지 않는다**: 작은 묶음 여러 개를 임계값까지 채워 붙이는 packing은 하지 않는다(요청 범위 밖, 단순하게).
- **`chunk_key`**: 첫 조각은 기존 `ecfr/{node_key}/0` 그대로(표의 `parent_chunk_key`가 이걸 가리킨다), 나머지는 `ecfr/{node_key}/0-1`, `/0-2`… 조각 dict의 다른 필드(`node_key`, `parent_chunk_key=None`)는 기존 본문 청크와 같다. 조각들은 표 청크보다 **앞에**, `block_no` 순서로 나온다.
- **표 블록은 묶기 대상에서 제외**(지금처럼 `body_block_nos`만 대상). `block_nos`가 빈 본문 청크(표만 있는 노드)는 기존대로 그대로 내보낸다(SUU-78 필터가 뒤에서 거른다).
- **실제 데이터 규모** (2026-09-17 DB): 40,000자 넘는 본문 55개, 최대 `appendix-Appendix-A-to-Part-63` 1,055,704자. 재귀가 깊어도 성능 문제 없을 크기.
