# SUU-44 feat(db): 파싱 결과를 jsonl로 저장하고 목차와 대조

## 목표
1단계가 받아둔 `raw/{기준일}/` 원본을 SUU-41~43 파서로 돌려 `parsed/{기준일}/{PARSER_VERSION}/`에 `nodes.jsonl`·`blocks.jsonl`·`quality_report.json` 세 파일을 쓰고, 목차 개수 일치·사라진 글 0 이면 `succeeded`, 아니면 `failed`로 report에 남긴다. 이 파일들이 3단계 DB 적재의 입력이다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/1_eCFR/ecfr_parse.py`
  - `PARSER_VERSION = "v1"` (모듈 상수. 출력 폴더 이름이자 report 값)
  - `parse_release(root: Path, as_of: str) -> dict` — report dict를 돌려주고, 같은 내용을 `quality_report.json`에 쓴다
  - `__main__` — `ecfr_collect.py`와 같은 모양
- 그대로 쓰기만 (수정 금지): `ecfr_nodes.py`(`parse_nodes`), `ecfr_blocks.py`(`parse_blocks`), `ecfr_labels.py`(`assign_label_paths`), `ecfr_structure.py`(`find_part`, `count_by_type`)
- 이미 있음 (수정 금지): `[2] db/tests/1_ecfr/test_ecfr_parse.py`, fixture `ecfr_part63_sample.xml`·`ecfr_structure_sample.json`

## 안 하는 것
- `references.jsonl`, `assets.jsonl`, DB 적재, `_SUBSTITUTE_DATE_` 치환 (뒤 티켓)
- 네트워크. raw 폴더가 없으면 그냥 예외로 끝난다 (held 같은 상태 없음)
- `tests/` 아래 수정, 기존 `ecfr_*.py` 수정, 새 의존성 (`lxml`은 이미 있음)
- 실패 시 파일 지우기 — 세 파일은 항상 쓴다. 합격 여부는 report의 `status`만 본다

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 세 파일이 생기고 report의 `node_counts` = `structure_counts`, `lost_text = 0`, `status = succeeded`. `nodes.jsonl`은 `parse_nodes` 결과 그대로, `blocks.jsonl`은 조문·부록마다 `parse_blocks → assign_label_paths` 결과 + `node_key` | `test_writes_three_files_and_report_passes` |
| 두 번 실행하면 `nodes.jsonl`·`blocks.jsonl` 바이트가 똑같음 (줄 끝 LF, 시각은 report에만) | `test_second_run_writes_identical_bytes` |
| 목차와 개수가 다르면 `status = failed` (report 파일도 `failed`), 예외 없이 끝남. `__main__`은 `failed`면 exit 2 | `test_fails_when_counts_differ_from_structure` |

테스트 파일: `[2] db/tests/1_ecfr/test_ecfr_parse.py`

## Codex 메모

### 1. 입력 — manifest에서 원본 찾기
`root / "raw" / as_of / "manifest.json"`은 `save_raw`가 만든 목록(list)이다. 항목 모양:
```json
{"name": "title-40-part-63.xml", "path": "raw/2026-09-11/<sha256>/title-40-part-63.xml", "sha256": "…", …}
```
- `name == "title-40-structure.json"` 항목과 `name == "title-40-part-63.xml"` 항목을 찾는다. 같은 이름이 여러 개면 **마지막 것**
- 파일 위치 = `root / entry["path"]`. report의 `structure_sha256`·`xml_sha256` = `entry["sha256"]` (다시 계산할 필요 없음)
- 목차 개수 = `count_by_type(find_part(json.loads(structure_bytes), "63"))` — 1단계 run.json의 `counts`와 같은 식

### 2. 노드 — `parse_nodes(xml_bytes)` 그대로
`nodes.jsonl` 한 줄 = `parse_nodes`가 준 dict 하나, 칸 12개 그대로 (`node_key, parent_key, node_type, identifier, heading, reserved, sort_order, hierarchy_path, citation, source_locator, xml_fragment, content_hash`). 더하거나 빼지 않는다. 문서 순서(= `sort_order`).

`node_counts` = `node_type`별 개수에서 **`part`를 뺀 것** (목차 `count_by_type`도 Part 자신은 안 센다). fixture: `{"subpart": 5, "subject_group": 3, "section": 9, "appendix": 4}`.

### 3. 블록 — 원본 트리를 다시 걸어야 한다
`parse_blocks`는 살아 있는 lxml 요소를 받고, `source_locator`에 **원본 파일의 줄 번호**를 쓴다. `xml_fragment`를 다시 파싱하면 줄 번호가 조각 기준으로 바뀌므로 안 된다. 그래서:
```python
parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True)  # parse_nodes 와 같은 옵션
tree_root = etree.fromstring(xml_bytes, parser)
elements = [e for e in tree_root.iter()
            if e.tag in _STRUCTURAL_TAGS and e.get("TYPE", "").upper() in _TYPE_NAMES]
```
`_STRUCTURAL_TAGS`·`_TYPE_NAMES`는 `ecfr_nodes`에서 import 한다 (복사하면 두 곳이 어긋난다). 이 필터가 `parse_nodes`와 같으므로 `elements[i]` ↔ `nodes[i]`. 확인용으로 `elements[i].get("N") == nodes[i]["identifier"]`를 assert 해도 좋다.

`node_type in {"section", "appendix"}`인 노드만:
```python
blocks = assign_label_paths(parse_blocks(element))
rows += [{"node_key": node["node_key"], **block} for block in blocks]
```
칸 9개: `node_key, block_no, kind, text_content, markup, source_locator, parse_status, label_path, label_status`. 순서 = 노드 순서 → `block_no`. 예약 조문은 `parse_blocks`가 `[]`를 주므로 줄이 없다. 상위 노드(part/subpart/subject_group)는 블록을 만들지 않는다.

### 4. `lost_text` — 블록 글 ≠ 원문 글인 조문·부록 수
조문·부록 노드마다 아래 둘을 비교해 다르면 +1:
```python
def _node_text(element):            # HEAD 를 뺀 노드 안 모든 글. 자식 사이 꼬리 글(tail)도 포함
    parts = [element.text or ""]
    for child in element:
        if child.tag != "HEAD":
            parts.append("".join(child.itertext()))
        parts.append(child.tail or "")
    return " ".join("".join(parts).split())

block_text = " ".join(" ".join(b["text_content"] for b in blocks).split())
```
예약 노드는 본문이 비어 있고 블록도 `[]`라 자연히 0 — 예외 처리 불필요. 진짜 파일에서도 0 이다 (아래 8).

### 5. 파일 쓰기 — 바이트가 매번 같아야 한다
```python
out = root / "parsed" / as_of / PARSER_VERSION
out.mkdir(parents=True, exist_ok=True)
data = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode("utf-8")
(out / "nodes.jsonl").write_bytes(data)     # 텍스트 모드로 열면 Windows 에서 \r\n 이 붙는다. bytes 로 쓴다
```
- jsonl 안에 시각·uuid·경로 같은 실행마다 달라지는 값을 넣지 않는다
- 덮어쓴다 (append 아님). `.part` 임시 파일은 안 써도 된다
- `quality_report.json`은 run.json처럼 `json.dumps(report, ensure_ascii=False, indent=2)`

### 6. report dict — 이 12칸, 이 순서
| 칸 | 값 |
|---|---|
| `as_of` | 인자 그대로 (`"2026-09-11"`) |
| `parser_version` | `PARSER_VERSION` |
| `status` | `"succeeded"` ↔ `node_counts == structure_counts and lost_text == 0`, 아니면 `"failed"` |
| `structure_sha256` / `xml_sha256` | manifest 항목의 `sha256` |
| `structure_counts` | 1번의 목차 개수 dict |
| `node_counts` | 2번 (part 제외) |
| `lost_text` | 4번 정수 |
| `block_kinds` | `kind`별 개수 dict. `other` 개수는 여기 (`block_kinds["other"]`) |
| `label_statuses` | `label_status`별 개수 dict. `uncertain` 개수는 여기 |
| `started_at` / `finished_at` | `datetime.now(timezone.utc).isoformat()` — collect의 `_now()`와 같음 |

`other`·`uncertain`은 `Counter`가 세므로 0개면 키가 없다 (fixture는 `label_statuses == {"ok": 30, "inherited": 35}`). 파일에 쓴 dict와 돌려주는 dict가 똑같아야 한다 (테스트가 `==` 비교).

### 7. 실행 입구
```python
if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2] / "1) eCFR"                       # → "[2] db/1) eCFR"
    raw = root / "raw"
    as_of = sys.argv[1] if len(sys.argv) > 1 else max(p.name for p in raw.iterdir() if p.is_dir())
    report = parse_release(root, as_of)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report["status"] == "succeeded" else 2)
```
`python "[2] db/pipeline/1_eCFR/ecfr_parse.py"` (기준일 생략 → raw 폴더 중 가장 최근 날짜) 또는 `… ecfr_parse.py 2026-09-11`. `parsed/`는 이미 `.gitignore`에 있다.

### 8. 진짜 파일(26 MB, 2026-09-11) 기대치 — 이미 확인함
- 노드 3,771 (part 1 + `{"subpart": 158, "subject_group": 492, "section": 2473, "appendix": 647}`) = 목차와 일치
- 블록 71,700: paragraph 65,188 · citation 1,910 · extract 1,108 · image 1,026 · heading 996 · table 784 · formula 481 · note 193 · editorial_note 6 · footnote 6 · **other 2**
- `label_statuses`: ok 55,330 · inherited 16,330 · **uncertain 40**
- `lost_text` 0 (꼬리 글 포함해도 0). 예약 조문·부록 90개 모두 본문 없음
- 파싱 약 4초. `parse_nodes`와 블록용 트리 파싱을 각각 하므로 XML을 두 번 읽는데, 그래도 몇 초라 괜찮다

### 9. 주의
- 표준 라이브러리 + `lxml`만. 100줄 안팎
- `parse_release`는 `root`가 `Path`가 아닐 수도 있으니 `Path(root)`로 감싼다 (테스트는 `tmp_path`를 준다)
- 테스트는 `save_raw`로 raw 폴더를 만든다 → manifest 모양은 1번과 정확히 같다
