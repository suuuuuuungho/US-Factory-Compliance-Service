# SUU-88 fix(db): 본문 글자 사이 불필요한 공백을 없앤다

## 목표
`parse_blocks`의 `text_content`에서 인라인 태그(`<E>` 등) 앞뒤에 끼어드는 공백을 없앤다. `(1) The date`가 `( 1 ) The date`로 나오지 않는다.

## 건드릴 파일
- 고칠 것: `[2] db/pipeline/1_eCFR/ecfr_blocks.py`의 `_text_content` — 마지막 줄 한 곳
- 고칠 것: `[2] db/tests/1_ecfr/test_ecfr_blocks.py` — 이미 작성됨 (빨강 확인 완료: 2 failed, 4 passed)

## 안 하는 것
- 표 행(`\n`)/셀(`" | "`) 구분 규칙(SUU-83)은 그대로
- `parse_blocks`의 다른 로직, 다른 파서 파일, 재적재(SUU-87)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 문단 안 인라인 태그 앞뒤에 공백이 안 생긴다 (`(1) The date—(i) Applicability.`, `10−3 gram`) | `test_paragraph_inline_tags_do_not_add_spaces` |
| 표 셀 안 인라인 태그도 마찬가지이고 셀 구분 `" | "`은 유지된다 (`>2.5 | (a) 95`) | `test_table_cell_inline_tags_do_not_add_spaces` |
| SUU-83 표 경계 테스트·기존 3개 회귀 없음 | `test_table_text_content_keeps_row_and_column_boundaries` 외 기존 |

## Codex 메모
- **원인**: SUU-83(PR #59)이 `_text_content`의 일반 텍스트 처리를 `" ".join("".join(element.itertext()).split())` → `" ".join(" ".join(element.itertext()).split())`으로 바꿨다. `itertext()`는 인라인 태그 경계마다 조각을 나누므로 `" ".join`이 태그 앞뒤에 공백을 넣는다.
- **고치는 법**: 안쪽 `" ".join`을 `"".join`으로 되돌린다. 표 셀도 같은 함수를 재귀 호출하므로 한 줄로 둘 다 고쳐진다. 그 외 수정은 필요 없다.
- **실측**: 2026-09-17 Part 63 재파싱에서 본문 블록 6,223개가 이 공백 때문에 바뀌었다. 고치면 SUU-83 대비 바뀌는 블록은 표 784개만 남아야 한다.
