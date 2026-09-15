# SUU-49 feat(db): ADI 검색 폼 3단계를 지나 결과 HTML 받기

## 목표
ADI 검색 폼을 홈(GET) → 조건 확인(POST) → 결과(POST)로 지나가, 전체 목록이 든 결과 HTML과 요청 정보를 돌려준다. SUU-48 `parse_results`가 읽을 HTML을 받아오는 단계.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/4_ADI+CAA/adi_fetch.py` — `fetch_results(category="ALL", *, request=None) -> dict`, `HOME_URL`, `build_opener()`
- 이미 있음 (수정 금지): `[2] db/tests/test_adi_fetch.py`, fixture `adi_home_form.html`(홈 검색 폼, 긴 select 잘라냄)·`adi_review_form.html`(확인 페이지, hidden 43개, category=MACT)·`adi_results_sample.html`(SUU-48 것 재사용)
- 참고만: `[2] db/pipeline/1_eCFR/ecfr_fetch.py`(주입 패턴), `adi_results.py`(다음 단계가 이 HTML을 읽음)

## 안 하는 것
- 결과 파싱 (SUU-48 `parse_results`가 함), `raw/` 저장·run.json (수집 실행 티켓)
- 상세(Abstract)·PDF 받기, 재시도·429·페이지 넘기기, 분류별 분할 수집
- 총건수 ≠ 행 수 검사 (수집 실행 티켓), `tests/` 아래·`pyproject.toml`·다른 `adi_*.py` 수정
- 새 의존성 — 표준 라이브러리만 (`urllib`, `http.cookiejar`, `re`). lxml 안 써도 된다

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 요청 3번을 순서대로: GET `HOME_URL` (본문 없음) → POST 홈 폼 action(`fuseaction=home.dsp_review_critieria`, `categoryvalue`=인자) → POST 확인 폼 action. action은 각 페이지에서 읽은 세션 포함 주소 | `test_walks_three_requests_in_order` |
| 확인 페이지 `<FORM>`~`</FORM>`의 hidden 43개를 이름·값 그대로 결과 요청 본문에. 값 속 `>`(`instr(category,'MACT') > 0`)도 온전 | `test_forwards_all_review_hidden_fields` |
| 결과 body·source_url·final_url·http_status·media_type·byte_size 를 dict로 돌려줌 | `test_returns_results_body_and_metadata` |
| 기본 요청기 `build_opener()`는 `HTTPCookieProcessor`+`CookieJar`를 가짐 (세션 쿠키 이어짐) | `test_default_requester_keeps_cookies` |
| 홈/확인 페이지에서 해당 `fuseaction` 폼을 못 찾으면 `ValueError` | `test_raises_when_form_missing` |

테스트 파일: `[2] db/tests/test_adi_fetch.py`

## Codex 메모

### 1. 주입받는 요청 함수 — `request(url, data=None)`
- eCFR `ecfr_fetch`처럼 네트워크를 함수로 분리한다. `fetch_results(category, *, request=None)`. `request=None`이면 기본 요청기를 만들어 쓴다
- `request(url, data=None)` 규약:
  - `data is None` → **GET**. `data`가 list[(name, value)] → **POST** (`urlencode(data, doseq=True)`)
  - 돌려주는 응답 객체는 `.body: bytes`, `.final_url: str`, `.http_status: int`, `.media_type: str`, `.byte_size: int`를 가진다 (테스트의 `FakeResponse`가 이 모양)
- 테스트는 `request`를 가짜(`Recorder`)로 넣어 홈→확인→결과 순으로 페이지를 돌려주고, 부른 `(url, data)`를 검사한다. **네트워크·파일 접근 없음**

### 2. 세 요청
```python
HOME_URL = "https://cfpub.epa.gov/adi/"

home = request(HOME_URL)                                    # 1. GET
action1, _ = _form(home.body, "home.dsp_review_critieria")  # 홈 폼 action
review = request(urljoin(HOME_URL, action1), criteria)      # 2. POST 조건
action2, hidden = _form(review.body, "home.dsp_show_results_table")
results = request(urljoin(HOME_URL, action2), hidden)       # 3. POST 결과
```
- action은 상대 주소(`index.cfm?CFID=…`)라 `urljoin(HOME_URL, action)`으로 절대 주소를 만든다. **주소에 세션 값(CFID/CFTOKEN)이 있으니 고정 주소를 쓰면 안 되고 페이지에서 읽는다**
- 2단계 POST 본문(`criteria`)은 이 순서·이 값 (categoryvalue만 인자):
  `fuseaction=home.dsp_review_critieria`, `controlnumvalue=`, `recentupdatevalue=ALL`, `categoryvalue=<category>`, `regionvalue=ALL`, `begindate=`, `enddate=`, `letterauthortext=`, `wordsearchtext=`, `subpartvalue=ALL`, `cfrvalue=ALL`
- 3단계 POST 본문은 확인 페이지 hidden 43개 그대로 (아래 3)

### 3. `_form(page, fuseaction)` — regex로 읽는다 (lxml 금지)
- 확인 페이지의 `<FORM>`은 `<table>` 안에서 열리고 `</table>`이 먼저 나와서 **lxml은 폼을 거기서 닫아 hidden 1개만 본다.** 나머지 42개가 사라진다 → 서버가 "zero determinations"를 준다. 그래서 원문 문자열에서 `<FORM …>` … `</FORM>` 사이를 직접 읽는다
- 태그·속성 정규식 (따옴표 안 `>`를 존중해야 한다. hidden 값에 `instr(category,'MACT') > 0`이 있다):
```python
_TAG = re.compile(r'''<(form|input)\b((?:\s+[\w-]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+))?)*)\s*/?>''', re.I)
_ATTR = re.compile(r'''([\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))''')
```
- 각 `<form>`마다 그 폼 안 hidden `(name, value)`을 모으고, `("fuseaction", fuseaction)`이 들어 있으면 그 폼의 action과 hidden 목록을 돌려준다. 못 찾으면 `ValueError`
- 태그 이름·속성 이름은 소문자로 비교 (`TYPE="Hidden"`, `NAME=`, `VALUE=` 대문자 섞임). value 없는 hidden은 `""`

### 4. 기본 요청기 — 쿠키
```python
def build_opener():
    return urllib.request.build_opener(HTTPCookieProcessor(CookieJar()))
```
- 세션 쿠키(CFID/CFTOKEN)가 세 요청에 이어져야 결과가 온다. `build_opener()`로 opener 하나를 만들어 세 요청에 모두 쓴다
- 요청에 `User-Agent`(우리 이름)를 붙인다 (계획 [1]-5 정중한 수집). 서버가 20초+ 걸리니 `timeout`은 180초 이상 (`requesttimeout=180`)

### 5. 돌려주는 dict
```python
{"body": results.body, "source_url": urljoin(HOME_URL, action2),
 "final_url": results.final_url, "http_status": results.http_status,
 "media_type": results.media_type, "byte_size": results.byte_size}
```
- 실제로 2026-09-15에 category=ALL로 지나가니 결과 3.9 MB, `results_length=3825`, 22초였다. category=MACT면 762행

### 6. 흐름
Codex가 `adi_fetch.py` 작성 → `python -m pytest` 초록(45개) → commit·push·PR (제목 = 이 파일 첫 줄 + ` (SUU-49)`) → 사용자 merge
