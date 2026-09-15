# SUU-41 feat(db): Part 63 XML을 목차와 같은 노드 표로 변환

## 목표
Part 63 XML을 읽어 Part·Subpart·중간제목·조문·부록을 한 줄씩 적은 노드 목록으로 만든다. 종류별 개수가 목차와 같아야 한다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/1_eCFR/ecfr_nodes.py`
  - `parse_nodes(xml_bytes: bytes) -> list[dict]`
- 이미 있음 (Claude가 넣음): `requirements.txt` (`lxml==6.1.3`), `[2] db/tests/fixtures/ecfr_part63_sample.xml`

## 안 하는 것
- 본문 블록 나누기 (SUU-42), 문단 번호 `label_path` (SUU-43), 파일 저장·목차 대조 (SUU-44)
- `_SUBSTITUTE_DATE_` 치환, 이미지 다운로드, 조문 인용 추출
- `tests/` 아래 파일 수정. 기존 `ecfr_*.py` 수정. 새 의존성 추가 (lxml만 허용)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 샘플 XML의 종류별 개수 = 샘플 목차 (subpart 5·subject_group 3·section 9·appendix 4), Part 1개, `sort_order`는 문서 순서 0부터 | `test_node_counts_match_structure_sample` |
| `[Reserved]` 노드 3개만 `reserved=True`. Part 바로 아래 조문·부록의 `parent_key`는 `40/63`, 중간제목 아래 조문의 부모는 중간제목 | `test_reserved_flag_and_part_level_parent` |
| `node_key` 전부 유일, `parent_key`는 존재하는 키. `hierarchy_path`·`citation`·`heading`·`source_locator`·`xml_fragment`·`content_hash` 값이 맞음 | `test_node_keys_unique_and_hierarchy_path` |

테스트 파일: `[2] db/tests/test_ecfr_nodes.py`

## Codex 메모

### 입력 XML 모양 (진짜 26MB 파일과 샘플이 같은 모양)
```
DIV5 N="63" TYPE="PART"            ← 루트. HEAD, AUTH, SOURCE
  DIV6 N="A" TYPE="SUBPART"        ← HEAD, SOURCE(가끔 EDNOTE)
    DIV8 N="63.1" TYPE="SECTION"   ← HEAD + 본문(P, EXTRACT, DIV/TABLE, img, MATH, NOTE, CITA …)
    DIV9 N="Table 1 to Subpart A of Part 63" TYPE="APPENDIX"
  DIV6 N="J"
    DIV7 N="ECFRad8028a5975965e" TYPE="SUBJGRP"   ← 중간 제목. HEAD만
      DIV8 …
  DIV8 N="63.569-63.599"           ← Part 바로 아래 조문도 있다 (깊이를 가정하지 말 것)
  DIV9 N="Appendix A to Part 63"   ← Part 바로 아래 부록
```
- `TYPE` → `node_type`: `PART→part`, `SUBPART→subpart`, `SUBJGRP→subject_group`, `SECTION→section`, `APPENDIX→appendix`
- DIV6~DIV9 자식을 **재귀**로 돌면서 문서 순서대로 노드를 만든다. 자식 DIV가 아닌 태그(HEAD, P …)는 이 티켓에서 무시.

### 파서
```python
from lxml import etree
parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True)
root = etree.fromstring(xml_bytes, parser)
```
(외부 엔터티·DTD 끔 = 계획서 2-1 요구. `huge_tree`는 26MB 원본용)

### 필드 규칙
| 필드 | 값 |
|---|---|
| `node_key` | 부모 키 + `/` + 자기 조각. Part는 `40/63`. 조각 = `subpart-{N}` / `subject-group-{N}` / `section-{N}` / `appendix-{N}`. **N 안의 공백은 `-`로** (대소문자 그대로). 예: `40/63/subpart-A/appendix-Table-1-to-Subpart-A-of-Part-63` |
| `parent_key` | 부모 노드의 `node_key`. Part는 `None` |
| `identifier` | `N` 속성 그대로 |
| `heading` | `HEAD` 안 글자 전부(`itertext`) → 공백 정리 `" ".join(text.split())`. 예: 끝 줄바꿈 제거 |
| `reserved` | `"[reserved]" in heading.lower()` (진짜 데이터에서 109개 전부 본문 없음) |
| `sort_order` | 문서 순서 정수, Part가 0 |
| `hierarchy_path` | Part부터 자기까지 `heading` 배열 |
| `citation` | `hierarchy_metadata` 속성(JSON)의 `citation`. **DIV5·DIV6·DIV7은 `&quot;`로 한 번 더 escape 되어 있음** → 값에 `&quot;`가 있으면 `html.unescape` 후 `json.loads`. DIV8·DIV9는 바로 `json.loads` |
| `source_locator` | `f"line:{element.sourceline}"` |
| `xml_fragment` | section·appendix: `etree.tostring(el, encoding="unicode", with_tail=False)`. part·subpart·subject_group: **자식 DIV6~9를 뺀 복사본**을 같은 방식으로 (상위 노드에 자식 전체를 중복 저장하지 않기 위해) |
| `content_hash` | `hashlib.sha256(xml_fragment.encode("utf-8")).hexdigest()` |

### 주의
- 샘플에서 `[Reserved]`는 Subpart K, `§§ 63.569-63.599`, `Tables 14-14b to Subpart G of Part 63` 3개.
- 63.1의 `source_locator`는 `line:16` (샘플 파일 기준). lxml `sourceline`은 태그 시작 줄.
- 반환은 `dict`의 `list`. dataclass를 써도 되지만 테스트는 `n["node_key"]`처럼 dict로 읽는다.
- 진짜 데이터 검증(목차 158/492/2473/647와 일치)은 merge 후 Claude가 돌린다. 코드에 26MB 파일 경로를 넣지 않는다.
