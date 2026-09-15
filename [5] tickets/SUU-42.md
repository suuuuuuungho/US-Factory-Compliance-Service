# SUU-42 feat(db): 조문 본문을 종류별 블록으로 순서대로 나눔

## 목표
조문(DIV8)·부록(DIV9) 하나의 본문을 문단·소제목·표·그림·수식·인용문·참고·각주·편집자 주·출처 블록으로 원문 순서대로 자른다. 글자가 하나도 사라지면 안 된다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/1_eCFR/ecfr_blocks.py`
  - `parse_blocks(element) -> list[dict]` — `element`는 lxml `DIV8`/`DIV9` 요소 하나
- 이미 있음: `[2] db/tests/1_ecfr/fixtures/ecfr_part63_sample.xml` (SUU-41), `requirements.txt` (`lxml`)

## 안 하는 것
- 문단 번호 `label_path` (SUU-43), 파일 저장·품질 보고 (SUU-44)
- 조문 인용 추출, 이미지 다운로드, 표를 글로 바꾸기
- `tests/` 아래 파일 수정. `ecfr_nodes.py` 등 기존 `ecfr_*.py` 수정. 새 의존성 추가 (lxml만 허용)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 샘플 조문 63.110의 `kind` 순서가 원문과 같음 (paragraph×3, heading, table, image, formula, extract, note, footnote, editorial_note, other, citation). `block_no`는 1부터, `source_locator`는 원본 줄번호, 필드는 6개 | `test_block_kinds_follow_document_order` |
| 블록 `text_content`를 다 이으면 본문(HEAD 제외) 글자와 같음. 블록 수 = HEAD 뺀 자식 수. 예약 노드는 블록 0개 | `test_no_text_is_lost_and_reserved_has_no_blocks` |
| 표 블록 `markup`에 `<TABLE` 원문 그대로. 그림 `src`는 전체 주소, 원본 트리는 안 바뀜. 모르는 태그(`STARS`)는 `kind=other` + `parse_status=unknown_tag` | `test_table_markup_kept_and_unknown_tag_marked` |

테스트 파일: `[2] db/tests/1_ecfr/test_ecfr_blocks.py`

## Codex 메모

### 규칙 한 줄
**DIV8/DIV9의 직접 자식 요소 하나 = 블록 하나.** 문서 순서 그대로. `HEAD`와 `DIV6`~`DIV9`(하위 노드)만 건너뛴다. 자식 안을 더 쪼개지 않는다 (EXTRACT 안의 FP, NOTE 안의 P, DIV 안의 TABLE 전부 그 블록 하나에 통째로 들어간다).

진짜 26MB 파일 조사: DIV8/DIV9 바로 밑 텍스트는 공백뿐(0건). 직접 자식 태그와 개수:
`P` 63,434 · `CITA` 1,910 · `FP-2` 1,182 · `EXTRACT` 1,108 · `img` 1,026 · `DIV` 784 (전부 안에 `TABLE`) · `HD2` 632 · `MATH` 481 · `FP-1` 272 · `HD1` 260 · `NOTE` 193 · `FP` 158 · `FP-DASH` 123 · `HD3` 104 · `FP1-2` 9 · `EDNOTE` 6 · `FTNT` 6 · `TCAP` 6 · `FP2-2` 4 · `STARS` 1 · `EXAMPLE` 1

### 태그 → kind
| 태그 | kind |
|---|---|
| `P`, `FP`, `FP-1`, `FP-2`, `FP1-2`, `FP2-2`, `FP-DASH`, `TCAP` | `paragraph` |
| `HD1`, `HD2`, `HD3` | `heading` |
| `DIV` (안에 `TABLE`이 있을 때) | `table` |
| `img` | `image` |
| `MATH` | `formula` |
| `EXTRACT` | `extract` |
| `NOTE` | `note` |
| `CITA` | `citation` |
| `FTNT` | `footnote` |
| `EDNOTE` | `editorial_note` |
| 그 밖의 전부 (`STARS`, `EXAMPLE`, TABLE 없는 `DIV` …) | `other` |

표 안에 안 적힌 태그를 짐작으로 추가하지 않는다. 모르는 건 `other`로 두면 SUU-44 품질 보고에 잡힌다.

### 필드
| 필드 | 값 |
|---|---|
| `block_no` | 1부터. 건너뛴 HEAD는 세지 않음 |
| `kind` | 위 표 |
| `text_content` | `" ".join("".join(child.itertext()).split())` — 공백 정리한 글. 그림은 `""` |
| `markup` | `etree.tostring(복사본, encoding="unicode", with_tail=False)` — 자식 요소 통째로. 표는 `<DIV width="100%">…<TABLE …>…</TABLE></DIV></DIV>` 껍데기 포함 |
| `source_locator` | `f"line:{child.sourceline}"` (원본 파일 줄번호. 요소를 재파싱하지 말 것) |
| `parse_status` | `unknown_tag`(kind가 other) → 아니면 `empty`(글도 없고 `img`도 없음) → 아니면 `ok` |

### 그림 주소
- 원문은 `<img src="/graphics/er04my98.004.gif"/>`. `markup`에서는 `src`를 `https://www.ecfr.gov` + 원래 값으로 바꾼다 (`/graphics/…`로 시작할 때만)
- 블록 자체가 `img`인 경우와, `MATH`·`EXTRACT`·`DIV` 안에 든 `img` 모두 바꾼다
- **반드시 `copy.deepcopy(child)`한 뒤 바꾼다.** 원본 트리를 바꾸면 테스트가 실패하고, SUU-44에서 노드 `xml_fragment`·`content_hash`가 흔들린다

### 예약 노드
`§§ 63.569-63.599 [Reserved]`처럼 예약된 조문은 HEAD만 있으므로 규칙대로 하면 자연히 `[]`. 따로 분기할 필요 없음.

### 샘플 63.110 (fixture 253~299줄) 기대값
```
block_no  kind            tag      줄
1~3       paragraph       P        255,256,257
4         heading         HD3      258
5         table           DIV      260
6         image           img      285
7         formula         MATH     286
8         extract         EXTRACT  288
9         note            NOTE     290
10        footnote        FTNT     293
11        editorial_note  EDNOTE   296
12        other           STARS    298   ← parse_status=unknown_tag
13        citation        CITA     299
```

### 참고
- 진짜 파일에 이 규칙을 적용하면: 조문·부록 3,120개 → 블록 71,700개 (paragraph 65,188 · heading 996 · table 784 · image 1,026 · formula 481 · extract 1,108 · note 193 · citation 1,910 · footnote 6 · editorial_note 6 · other 2), `empty` 10개(`FP-DASH`), 글자 사라진 노드 0개. merge 후 Claude가 다시 확인한다.
- 반환은 dict의 list. `node_key`는 넣지 않는다 (부르는 쪽이 안다).
- 안전한 파서는 부르는 쪽(테스트·SUU-44) 책임. 이 모듈은 요소만 받는다.
