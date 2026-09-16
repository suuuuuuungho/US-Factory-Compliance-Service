# SUU-83 fix(db): 표 셀 경계를 살려서 저장한다

## 목표
표(TABLE) 블록의 `text_content`를 셀 구분 없이 이어붙인 한 줄 문자열이 아니라, 행/열 경계가 살아있는 문자열로 만든다.

## 건드릴 파일
- `[2] db/pipeline/1_eCFR/ecfr_blocks.py` — `_text_content(element)`가 `kind == "table"`일 때는 지금처럼 `itertext()`를 그냥 이어붙이지 말고, `TR`마다 줄바꿈(`\n`)으로, 각 행 안 `TD`/`TH` 셀마다 `" | "`로 구분해서 문자열을 만든다. `CAPTION`이 있으면 첫 줄에 캡션 텍스트를 넣는다. 셀 텍스트 자체는 지금처럼 공백 정규화(`" ".join(...split())`)해서 넣는다.
- `parse_blocks`가 `_text_content(child)`를 호출하는 지점은 그대로 두고, `_text_content` 내부에서 `kind`(또는 `_is_table(element)`)로 분기한다.

## 안 하는 것
- 병합 셀(`rowspan`/`colspan`) 완벽 처리 — 있는 그대로 셀 하나로 취급
- 표가 아닌 다른 블록 종류(`paragraph`, `note` 등) 처리 방식 변경
- `ecfr_ingest.py` 재실행(Part 63 재적재)은 이 코드가 머지된 뒤 Claude가 직접 실행

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 표 블록의 `text_content`가 행마다 줄바꿈, 셀마다 `" | "`로 구분된 문자열이다 | `test_table_text_content_keeps_row_and_column_boundaries` |
| 표가 아닌 블록 포함, 전체 텍스트 유실은 없다(구조 문자 제외하고 원문과 같은 단어) | `test_no_text_is_lost_and_reserved_has_no_blocks` (기존 테스트, 표 구분자 `|`를 무시하도록 비교 방식만 수정함) |

## Codex 메모
- `_is_table(element)`가 이미 있다 (`element.tag == "DIV" and element.find(".//TABLE") is not None`) — `_text_content`에서 이 함수로 분기하면 된다.
- 행은 `element.findall(".//TR")`로 문서 순서대로 가져오면 `THEAD`/`TBODY`/`TFOOT` 상관없이 순서가 유지된다.
- 각 행의 셀은 `[c for c in tr if c.tag in ("TD", "TH")]`로 뽑고, 각 셀 텍스트는 기존 `_text_content`가 하던 것과 동일하게 `" ".join("".join(cell.itertext()).split())`로 정규화한다(재사용 가능하면 재사용).
- `CAPTION`은 `element.find(".//CAPTION")`으로 찾고, 있으면 같은 방식으로 정규화해서 첫 줄에 넣는다.
- `markup` 필드(원본 XML)는 건드리지 않는다 — `text_content`만 바꾼다.
