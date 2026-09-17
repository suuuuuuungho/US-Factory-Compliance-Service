# SUU-88 fix(db): 본문 글자 사이 불필요한 공백을 없앤다

## 목표
`parse_blocks`의 `text_content`에서 글자 중간에 끼는 인라인 태그(`<E>`, `<sub>`, `<sup>` 등) 앞뒤 공백을 없앤다. 단 `<br/>`와 블록형 자식(`<HED>`, `<PSPACE>` 등)은 단어 경계로 남긴다.

## 건드릴 파일
- 고칠 것: `[2] db/pipeline/1_eCFR/ecfr_blocks.py` — `flat_text(element) -> str` 추가(아래 규칙), `_text_content`의 일반 텍스트·표 셀 처리가 이걸 쓰게, `__all__`에 `flat_text` 추가
- 고칠 것: `[2] db/pipeline/1_eCFR/ecfr_parse.py`의 `_node_text` — `" ".join(child.itertext())` 대신 `ecfr_blocks.flat_text(child)`를 쓴다 (잃어버린 글자 검사 기준을 블록과 같은 규칙으로 맞춤)
- 고칠 것: `[2] db/tests/1_ecfr/test_ecfr_blocks.py` — 이미 작성됨 (빨강 확인 완료: 3 failed, 4 passed)

## 안 하는 것
- 표 행(`\n`)/셀(`" | "`) 구분 규칙(SUU-83)은 그대로
- `parse_blocks`의 다른 로직, `ecfr_nodes.py`, 재적재(SUU-87)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 문단 안 `<E>` 앞뒤에 공백이 안 생긴다 (`(1) The date—(i) Applicability.`, `10−3 gram`) | `test_paragraph_inline_tags_do_not_add_spaces` |
| 표 셀 안 `<E>`도 마찬가지이고 셀 구분 `" | "`은 유지 (`>2.5 | (a) 95`) | `test_table_cell_inline_tags_do_not_add_spaces` |
| `<br/>`는 단어 경계(`efficiency requirement`), `<sub>`/`<sup>`는 붙임(`H2O`, `103`) — 문단·표 셀 모두 | `test_br_is_a_word_boundary_but_other_inline_tags_are_not` |
| SUU-83 표 경계·글자 손실 없음 테스트 회귀 없음 | `test_table_text_content_keeps_row_and_column_boundaries`, `test_no_text_is_lost_and_reserved_has_no_blocks` |
| 파싱 품질 보고서가 `succeeded` (블록 텍스트 == 노드 텍스트) | `[2] db/tests/1_ecfr/test_ecfr_parse.py::test_writes_three_files_and_report_passes` (기존) |

## Codex 메모
- **왜 한 줄 수정으로 안 되나**: SUU-83이 `"".join(itertext())`를 `" ".join(itertext())`로 바꾼 이유는 `efficiency<br/>requirement`가 붙는 것을 막기 위해서였다. 그런데 이 방식은 `(<E>1</E>)`, `H<sub>2</sub>O`도 띄운다. 원문 Part 63 XML 실측(2026-09-17): 글자 사이에 공백 없이 끼는 태그는 `E` 7,202회, `sub` 500, `sup` 197, `I` 3, `SU` 1 (→ 붙여야 함), `br` 620회(→ 띄워야 함). 그래서 태그별로 달리 처리해야 한다.
- **규칙 (`flat_text`)**: 붙이는 태그 허용목록 `GLUE_TAGS = {"E", "SU", "I", "sub", "sup", "FTREF"}`. 그 외 모든 자식 요소(`br`, `HED`, `PSPACE`, `P`, `PRTPAGE` …)는 앞뒤에 공백 하나를 넣는다. 그 뒤 `" ".join(text.split())`으로 정규화하므로 공백이 겹쳐도 하나가 된다.
  ```python
  GLUE_TAGS = {"E", "SU", "I", "sub", "sup", "FTREF"}

  def flat_text(element):
      parts = [element.text or ""]
      for child in element:
          if isinstance(child.tag, str):  # 주석/PI 제외
              inner = flat_text(child)
              parts.append(inner if child.tag in GLUE_TAGS else f" {inner} ")
          parts.append(child.tail or "")
      return "".join(parts)
  ```
  `_text_content`의 일반 텍스트 반환은 `" ".join(flat_text(element).split())`. 표 분기는 `_text_content(cell)`을 재귀 호출하므로 셀도 같은 규칙을 탄다.
- **`ecfr_parse._node_text`도 같이**: 이 함수는 "블록 텍스트를 다 합치면 노드 텍스트와 같은가"를 검사하는 기준값이다. 지금은 `" ".join(child.itertext())`라 `<E>` 앞뒤가 띄어져 있어서 블록 쪽만 고치면 `lost_text`가 늘어나 `status == "failed"`가 된다. `parts.append(" ".join(child.itertext()))` → `parts.append(flat_text(child))`로 바꾼다. `from ecfr_blocks import flat_text, parse_blocks`.
- **검증 완료**: 위 두 파일 패치로 `[2] db/tests` 전체 142개 통과함(2026-09-17, 임시 패치로 확인).
- **실측**: 고친 뒤 Part 63 재파싱하면 SUU-83 대비 바뀌는 블록은 표 784개 + 인라인 태그 붙은 본문뿐이어야 하고, `( 1 )` 같은 패턴은 0건이어야 한다. SUU-87에서 확인한다.
