# SUU-90 fix(rag): 라벨 없는 큰 조문은 블록 순서대로 쪼갠다

## 목표
`build_chunks`의 `_split_body_blocks`가 `label_path`로 더 나눌 수 없는데도 `max_chars`를 넘는 묶음을 만나면, 블록을 `block_no` 순서대로 한도까지 채워서 여러 조각으로 만든다.

## 건드릴 파일
- 고칠 것: `[2] db/pipeline/5_rag/ecfr_chunks.py` — `_split_body_blocks`만. 도우미 `_pack_in_order(blocks, max_chars)` 하나 추가해도 됨
- 고칠 것: `[2] db/tests/5_rag/test_ecfr_chunks.py` — 이미 작성됨 (빨강 확인 완료: 3 failed, 13 passed)

## 안 하는 것
- `_group_at_label_depth`, `build_chunks` 본체, `chunk_key` 규칙(`/0`, `/0-1`…), 표 청크 처리 — 그대로
- 블록 하나를 글자 단위로 자르는 것 (블록은 최소 단위, SUU-84 규칙 유지)
- 작은 묶음끼리 합치는 packing — 라벨로 나뉜 조각은 지금처럼 그대로 둔다. 순서대로 채우기는 **라벨로 못 나눌 때만**
- `select_subpart_chunks`, `index_chunk`, `ecfr_embed.py`

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 라벨 없는 블록 여러 개가 한도를 넘으면 순서대로 채워 여러 조각. 각 조각 한도 안, 키 `/0`, `/0-1`, `/0-2`… | `test_unlabeled_blocks_over_limit_are_packed_in_order_within_limit` |
| 채우는 중 블록 하나가 단독으로 한도를 넘으면 그 블록만 한 조각, 그 뒤부터 다시 채운다 | `test_packing_keeps_single_oversized_block_whole_and_continues_after_it` |
| 이 깊이에서 묶음이 1개뿐이어도 더 깊은 라벨이 있으면 먼저 그 깊이로 나눈다(순서대로 채우기는 마지막 수단) | `test_single_top_label_group_is_split_at_deeper_label_before_packing` |
| 라벨 없는 조문도 한도 이하면 청크 1개 `/0` 그대로 | `test_unlabeled_section_within_limit_stays_one_chunk` |
| SUU-84 기존 테스트 전부 통과 (라벨로 나뉘는 결과는 변화 없음) | 기존 12개 |

## Codex 메모
- **지금 코드**(`ecfr_chunks.py` `_split_body_blocks`): `groups = _group_at_label_depth(blocks, depth)`가 1개 이하면 `return [blocks]`로 포기한다. 이 지점만 바꾼다:
  1. `blocks` 중 `len(label_path) > depth + 1`인 게 하나라도 있으면 → `_split_body_blocks(blocks, max_chars, depth + 1)` (더 깊은 라벨로 시도)
  2. 아니면 → 순서대로 채우기
- **순서대로 채우기 규칙**: 빈 `current`에서 시작해 블록을 하나씩 붙인다. `current`가 비어있지 않고 `_chunk_length(current + [block]) > max_chars`이면 `current`를 조각으로 확정하고 새로 시작한다. 빈 `current`에는 무조건 넣는다 → 혼자서 한도를 넘는 블록도 통째로 한 조각이 된다. 글자 수 기준은 기존 `_chunk_length`(`"\n\n".join`)를 그대로 쓴다
- **재귀 시작 조건 `len(blocks) <= 1 or _chunk_length(blocks) <= max_chars`는 그대로** — 한도 이하는 절대 안 쪼갠다
- **왜 1번(더 깊은 라벨)도 필요한가**: 2026-09-17 로컬 Part 63 전체로 돌려보면 한도 초과 청크가 **18개** 남는다. 라벨이 아예 없는 것(Appendix A to Subpart UUUUU 74k자 등 8개)도 있지만, `section-63.99`(53k자)처럼 라벨은 깊이 4까지 있는데 이 깊이 묶음이 하나뿐이라 멈춘 것도 있다. 두 규칙을 같이 넣은 시제품으로 돌리면 한도 초과 0개, 조각(`-` 붙은 키) 1,913 → 2,119개. 픽스처 XML 결과는 그대로(`-` 키 없음)
- 테스트 헬퍼: `_block(no, label_path, kind, text)`는 기본 50자(`[n]` + x 47개). `"\n\n"` 2자를 더하면 2개 = 102자, 3개 = 154자
