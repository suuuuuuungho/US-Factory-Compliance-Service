# SUU-47 feat(db): CAA Dashboard 표에서 회신 목록과 PDF 주소 읽기

## 목표
CAA Dashboard 페이지 HTML의 표(236행)를 읽어 한 행 = dict 하나인 목록으로 바꾼다. Safe Links로 감싸인 링크는 풀어서 `epa.gov` 실제 PDF 주소를 얻고, `Affected Subpart` 글자에서 Part·Subpart 쌍을 뽑는다. ADI+CAA 파이프라인의 첫 티켓이다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/4_ADI+CAA/adi_dashboard.py` — `parse_dashboard(html: bytes) -> list[dict]`
- 이미 있음 (수정 금지): `[2] db/tests/test_adi_dashboard.py`, fixture `[2] db/tests/fixtures/adi_dashboard_sample.html` (2026-09-15 실제 페이지에서 `<table>`만 잘라낸 것. Safe Links 안 직원 이메일만 `staff@epa.gov`로 바꿈)
- 이미 고침 (이 브랜치): `pyproject.toml` pythonpath에 `[2] db/pipeline/4_ADI+CAA` 추가, RAG 계획 [12]-2 티켓 순서

## 안 하는 것
- 네트워크로 페이지 받기, PDF 내려받기, `raw/` 저장, run.json (다음 티켓들)
- ADI 쪽 (검색 폼·Abstract), 회신 본문 파싱, DB 적재
- `canonical_url`이 None인 이유 칸, 날짜 파싱 (`link_text`는 글자 그대로만)
- 새 의존성 (`lxml`은 이미 있음), `tests/` 아래 수정, `pyproject.toml` 추가 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 표의 모든 행(236)이 dict 하나씩, 칸 8개가 이 순서로. 표 순서 그대로. `Part 63` 행 132, Subpart 여러 개인 행 42 | `test_every_row_becomes_one_dict_with_eight_fields` |
| Safe Links는 `url` 값을 풀어 `canonical_url`에 `https://www.epa.gov/...`. `source_url`은 추적 매개변수(`data`·`sdata`·`reserved`)를 뗀 주소. `epa.gov`가 아닌 주소·상대 주소는 `canonical_url = None`이되 행은 남김 | `test_safe_links_resolve_to_epa_url_without_tracking_data` |
| `Affected Subpart`에서 `{"part": "60", "subpart": "IIII"}` 쌍을 `;` 구분마다 하나씩. 전체 281쌍. 소문자 섞인 코드(`Db`) 그대로 | `test_affected_subpart_splits_into_part_subpart_pairs` |
| 네 열 중 하나라도 없는 표, 또는 표가 없으면 `ValueError` | `test_missing_column_raises` |

테스트 파일: `[2] db/tests/test_adi_dashboard.py`

## Codex 메모

### 1. 표 찾기
- 페이지에 `<table class="default" id="datatable">` 하나. `<thead>`의 `<th>` 네 개: `Facility Name`, `Title`, `Affected Subpart`, `Link to Responses`
- **id가 아니라 헤더 글자로 찾는다.** `<th>` 글자 네 개가 다 있는 첫 `<table>`을 쓰고, 열 위치는 헤더 순서에서 구한다 (열 순서가 바뀌어도 되게). 없으면 `ValueError`
- `<tbody>`의 `<tr>`마다 `<td>` 네 개. `<td>`가 없는 `<tr>`(헤더 행)은 건너뛴다
- lxml: `from lxml import html as lxml_html; doc = lxml_html.fromstring(html_bytes)`. `ecfr_nodes.py`처럼 `lxml`만 쓴다

### 2. 칸 8개, 이 순서
```python
{
    "source_system": "caa_dashboard",
    "facility_name": ...,          # td 글자
    "title": ...,                  # td 글자
    "affected_subpart_raw": ...,   # td 글자 그대로
    "link_text": ...,              # td 글자. 날짜("2020-06-16")일 수도, 파일명("Hyliion Response_9-11-25 (pdf) (176.91 KB)")일 수도
    "source_url": ...,             # 3번
    "canonical_url": ...,          # 3번. None 가능
    "affected_subparts": [...],    # 4번
}
```
- "td 글자" = `" ".join("".join(td.itertext()).split())`. 링크 칸에는 `<span class="document">`·`<svg>`·`<span class="document__meta">`가 섞여 있는데 이렇게 하면 `Hyliion Response_9-11-25 (pdf) (176.91 KB)`가 나온다
- 이름은 계획 `[1] docs/2) db/db 구축 계획/4_ADI+CAA 구축 계획.md` [3]-5 `adi_source_entry`의 칸 이름을 그대로 썼다. 나중에 적재 티켓이 이 dict를 그 표에 넣는다

### 3. 링크 — `source_url` / `canonical_url`
링크 칸의 첫 `<a href>`를 읽는다 (`<a>`가 없으면 둘 다 None). href 모양 세 가지:

| href | `source_url` | `canonical_url` |
|---|---|---|
| `https://gcc02.safelinks.protection.outlook.com/?url=https%3A%2F%2Fwww.epa.gov%2F...&data=05%7C02%7Cstaff%40epa.gov...&sdata=...&reserved=0` (234개) | `https://gcc02.safelinks.protection.outlook.com/?url=https%3A%2F%2Fwww.epa.gov%2F...` — **`url` 하나만 남긴다** | `url` 값을 한 번 푼 것: `https://www.epa.gov/system/files/documents/2022-05/King%20Systems%20Corp%20Response_6-16-20.pdf` |
| `https://www.epa.gov/system/files/documents/2025-09/hyliion-response_9-11-25.pdf` (1개) | href 그대로 | href 그대로 |
| `/%3Ab%3A/s/R4/APTMD/...?e=SIhi4U` — 깨진 SharePoint 상대 주소 (1개, Westrock) | href 그대로 | `None` |

- `urllib.parse.urlparse` + `parse_qs(query)["url"][0]` — `parse_qs`가 한 번 풀어 준다 (`%2520` → `%20`이 맞다. 두 번 풀지 않는다)
- `canonical_url`은 scheme `https` + host `www.epa.gov`일 때만. 아니면 `None`. 행을 버리지 않는다
- `data`(직원 이메일이 들어 있다)·`sdata`·`reserved`는 결과 어디에도 넣지 않는다. 테스트가 `json.dumps(rows)`에서 `%40epa.gov`·`data=`·`sdata=`·`reserved=`를 찾는다
- lxml이 `&amp;`를 `&`로 풀어 주므로 href를 그대로 `urlparse`하면 된다

### 4. `affected_subparts`
- 글자 예: `Part 60, IIII: Stationary Compression Ignition Internal Combustion Engines ; Part 60, JJJJ: Stationary Spark Ignition Internal Combustion Engines`
- `re.findall(r"Part\s*(\d+)\s*,\s*([A-Za-z]{1,7})\s*:", raw)` → `[("60", "IIII"), ("60", "JJJJ")]` → `[{"part": "60", "subpart": "IIII"}, ...]`. 이 패턴으로 236행 281쌍 전부 잡히는 것을 확인했다 (안 잡히는 조각 0)
- `part`·`subpart`는 문자열. 대소문자 그대로 (`Db`, `Ja`, `OOOOa` 같은 Part 60 코드가 있다). Part 60의 `AAAA`와 Part 63의 `AAAA`는 다른 것이라 part를 꼭 같이 둔다
- 쌍이 하나도 안 잡히면 빈 리스트 (지금 데이터엔 없다)

### 5. 실행 입구 없음
`__main__` 없이 함수 하나만. 페이지 받기·저장은 다음 티켓이 이 함수를 부른다. 표준 라이브러리 + `lxml`, 50줄 안팎.

### 6. 흐름
Codex가 `adi_dashboard.py` 작성 → `python -m pytest` 초록(36개) → commit·push·PR (제목 = 이 파일 첫 줄 + ` (SUU-47)`) → 사용자 merge
