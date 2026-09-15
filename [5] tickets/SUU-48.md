# SUU-48 feat(db): ADI 결과 표에서 Control Number 목록 읽기

## 목표
ADI 검색 결과 페이지 HTML의 표를 읽어 한 행 = dict 하나인 목록으로 바꾸고, 폼에 숨어 있는 서버 총건수를 같이 돌려준다. SUU-47(Dashboard 표 읽기)의 ADI 판.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/4_ADI+CAA/adi_results.py` — `parse_results(html: bytes) -> dict`
- 이미 있음 (수정 금지): `[2] db/tests/4_ADI+CAA/test_adi_results.py`, fixture `[2] db/tests/4_ADI+CAA/fixtures/adi_results_sample.html` (2026-09-15 Category=MACT 결과 762행에서 폼+표만 잘라냄. 처음 30행 + 특수 행 9개 = 39행. 세션 값 CFID/CFTOKEN은 지움)
- 참고만: `[2] db/pipeline/4_ADI+CAA/adi_dashboard.py` (같은 모양의 표 읽기. 수정 금지)

## 안 하는 것
- 검색 폼 3단계 넘기기·네트워크 (SUU-49), 상세 Abstract 읽기, PDF 내려받기, `raw/` 저장, DB 적재
- 날짜 파싱 (`letter_date_raw`는 글자 그대로), 총건수 ≠ 행 수일 때 실패 처리 (비교는 수집 실행 티켓)
- 새 의존성 (`lxml`만), `tests/` 아래 수정, `pyproject.toml` 수정 (pythonpath는 SUU-47에서 이미 추가됨)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 표의 모든 행(39)이 dict 하나씩, 칸 8개가 이 순서로. 표 순서 그대로. Control Number 중복 없음·문자열. `12/30/1899`는 글자 그대로, 작성자 빈 칸은 `None` | `test_every_row_becomes_one_dict_with_eight_fields` |
| `source_url` = `https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id=<Control Number>`. href에 CFID/CFTOKEN이 있어도 결과 어디에도 없음 | `test_source_url_has_no_session_token` |
| `Categories` 쉼표 나열 → 리스트. 반환 dict는 `{"results_length": int, "rows": [...]}` 이 순서, `results_length`는 hidden 값 그대로 (762, 행 수와 달라도 됨) | `test_categories_split_and_results_length_returned` |
| 열 7개 중 하나라도 없음 / `results_length` hidden 없음 / 표 없음 → `ValueError` | `test_missing_column_raises` |

테스트 파일: `[2] db/tests/4_ADI+CAA/test_adi_results.py`

## Codex 메모

### 1. 표 찾기 — Dashboard와 다른 점 두 가지
- 헤더가 `<th>`가 아니라 **`<td>`** 다. `<thead>` 안에 `<tr>` 두 개: 첫째는 `colspan="7"` 빈 칸 하나, 둘째가 진짜 헤더 (`<td><div><b>Control Number</b></div></td>` 모양). 글자로 뽑으면 이 7개:
  `Checkbox for Determination Details`, `Control Number`, `Title`, `Letter Date`, `Categories`, `Office`, `Letter Author`
- `adi_dashboard.py`처럼 **id가 아니라 헤더 글자로** 표를 찾고, 열 위치는 헤더 순서에서 구한다. `<thead>`의 `<tr>`들 중 7개 글자가 다 들어 있는 행을 헤더로 쓴다. 없으면 `ValueError`
- 행은 `<tbody>`의 `<tr>`, `<td>` 7개. 첫 칸은 체크박스(`<input name="control_number" type="checkbox" value="1800013">`)라 글자가 없다 — 쓰지 않는다
- "칸 글자" = `" ".join("".join(td.itertext()).split())` (Dashboard와 같음)

### 2. 서버 총건수
표 위 폼에 `<input type="hidden" name="results_length" value="762">`. `int(value)`. 없으면 `ValueError`. 행 수와 비교하지 않는다 — 계획 [1]-4의 "서버 총건수와 실제 고유 ID 수 대조"는 수집 실행 티켓이 이 두 값을 받아서 한다.

### 3. 반환 모양
```python
{
    "results_length": 762,
    "rows": [
        {
            "source_system": "adi",
            "control_number": "1800013",          # 문자열. "M200005", "Z200004", "1800013" 세 모양
            "title": "Alternative Monitoring Plan for Internal Floating Roof Storage Tanks",
            "letter_date_raw": "05/11/2018",       # 글자 그대로. "12/30/1899" 도 그대로
            "categories": ["MACT", "NSPS"],        # 쉼표로 나눠 strip. "Federal Plan" 처럼 공백 있는 값도 있다
            "office": "Region 5",
            "author": "Sara Breneman",             # 빈 칸이면 None
            "source_url": "https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id=1800013",
        },
        ...
    ],
}
```
- 키 순서 고정 (테스트가 `list(row) == FIELDS`, `list(result) == ["results_length", "rows"]`로 본다)
- 칸 이름은 계획 `4_ADI+CAA 구축 계획.md` [3]-5 `adi_source_entry`에서 가져왔다

### 4. `source_url` — 세션 값을 넣지 않는다
- 제목 칸의 링크는 실제 페이지에서 `index.cfm?fuseaction=home.dsp_show_file_contents&CFID=33954140&CFTOKEN=…&id=1800013` 이다. CFID/CFTOKEN은 그 세션에서만 유효하니 저장하면 안 된다 (계획 [1]-4)
- href를 쓰지 말고 **Control Number 칸 값으로 만든다**: `"https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id=" + control_number`. href의 `id=` 값은 늘 Control Number와 같다 (762행 전부 확인)
- 이 주소는 세션 없이도 PDF를 준다 (SUU-46에서 확인)

### 5. 실행 입구 없음
함수 하나만. 표준 라이브러리 + `lxml`, 50줄 안팎. `adi_dashboard.py`의 `_text`를 복사해도 되고 import 해도 된다.

### 6. 흐름
Codex가 `adi_results.py` 작성 → `python -m pytest` 초록(40개) → commit·push·PR (제목 = 이 파일 첫 줄 + ` (SUU-48)`) → 사용자 merge
