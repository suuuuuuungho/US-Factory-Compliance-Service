# SUU-35 feat(db): eCFR 목차에서 Part 63 가지와 항목 수 읽기

## 목표
Title 40 목차 JSON에서 Part 63 노드를 찾고, 그 아래 항목을 종류별로 센다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/1_eCFR/ecfr_structure.py`
- 이미 있음 (수정 금지): `[2] db/tests/test_ecfr_structure.py`, `[2] db/tests/fixtures/ecfr_structure_sample.json`

## 안 하는 것
- 네트워크로 목차 받아오기 (SUU-36)
- 본문 XML 파싱
- `ecfr_titles.py` 수정
- `tests/` 아래 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| `identifier`가 `63`인 part 노드를 찾는다 | `test_finds_part_63_node` |
| 없으면 `ValueError` | `test_missing_part_raises` |
| Part 63 아래 종류별 개수를 센다. 예약 항목도 포함 | `test_counts_descendants_by_type_including_reserved` |

## Codex 메모

테스트가 부르는 함수 2개:

```python
def find_part(structure: dict, part: str = "63") -> dict
def count_by_type(node: dict) -> dict[str, int]
```

- 목차 JSON 모양: 노드 하나 = `{"identifier", "label", "type", "reserved", ..., "children": [...]}`.
  `type`은 `title → chapter → subchapter → part → subpart → subject_group → section / appendix`.
  `children`이 없는 노드(leaf)도 있고, 예약 Subpart는 `"children": []`이다.
- `find_part`: 트리를 재귀로 내려가며 `type == "part"`이고 `identifier == part`인 첫 노드를 돌려준다.
  `identifier`는 문자열(`"63"`)이다. 못 찾으면 `ValueError`.
- `count_by_type`: 그 노드 **자신을 빼고** 모든 자손을 `type`별로 센다. `reserved`가 `true`여도 뺀다거나 따로 세지 않는다.
  결과는 보통 `dict`면 된다 (`Counter`를 돌려줘도 `==` 비교는 통과하지만 `dict`로 바꿔서 주는 게 깔끔).
- section·appendix는 subpart 바로 아래에도, subject_group 아래에도, Part 바로 아래에도 온다. 깊이를 가정하지 말고 전부 순회한다.
- 실제 Part 63(2026-09-10)은 subpart 158 · subject_group 492 · section 2,473 · appendix 647이다. 샘플은 그중 일부만 잘라낸 것이라 숫자가 작다.
- 표준 라이브러리만 쓴다. 새 패키지 추가 없음.
