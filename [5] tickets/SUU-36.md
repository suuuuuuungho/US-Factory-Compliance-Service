# SUU-36 feat(db): Part 63 원문 XML 받고 HTML 응답은 실패 처리

## 목표
eCFR 주소 하나를 gzip으로 받아 원래 바이트와 응답 정보를 돌려주고, HTML(접근 확인 화면)은 XML로 인정하지 않는다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/1_eCFR/ecfr_fetch.py`
- 이미 있음 (수정 금지): `[2] db/tests/1_ecfr/test_ecfr_fetch.py`

## 안 하는 것
- `ecfr_titles.py`, `ecfr_structure.py` 수정
- 파일 저장 (SUU-37), 전후 비교·실행 (SUU-38)
- 재시도·429 처리 (나중 티켓)
- `tests/` 아래 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| gzip 압축 응답을 풀어 원래 바이트를 돌려준다 | `test_decompresses_gzip_body` |
| 본문이 `<!DOCTYPE html` / `<html`로 시작하면 200이어도 오류 | `test_rejects_html_body_even_with_200` |
| 최종 URL·HTTP 상태·Content-Type·바이트 수를 함께 돌려준다 | `test_returns_final_url_status_type_and_size` |
| (범위) 목차·원문 XML 주소 만들기 | `test_builds_structure_and_part_xml_urls` |

## Codex 메모

테스트가 부르는 것 4개:

```python
@dataclass(frozen=True)
class Fetched:
    body: bytes        # 압축 푼 뒤
    source_url: str    # 요청한 주소
    final_url: str     # response.geturl() — 리다이렉트 후 최종 주소
    http_status: int   # response.status
    media_type: str    # Content-Type 헤더 그대로 (예: "application/xml; charset=utf-8")
    byte_size: int     # len(body)

def fetch(url: str) -> Fetched
def ensure_xml(body: bytes) -> bytes      # HTML이면 ValueError, 아니면 body 그대로
def structure_url(as_of: date, title: int = 40) -> str
def part_xml_url(as_of: date, title: int = 40, part: int = 63) -> str
```

- **import는 꼭 이 모양으로**: `from urllib.request import Request, urlopen`.
  테스트가 `ecfr_fetch.urlopen`을 monkeypatch 하기 때문에 `urllib.request.urlopen(...)`처럼 부르면 가짜가 안 끼워진다.
- 가짜 응답이 가진 것: `read()`, `headers.get(...)`, `geturl()`, `status`, `with` 문. 이것만 써라. `getcode()`, `info()`, `url` 속성은 없다.
- `fetch`는 `ecfr_titles.fetch_titles`와 같은 방식: `Request(url, headers={"Accept-Encoding": "gzip", ...})` → `with urlopen(request) as response:` → `Content-Encoding`에 `gzip`이 있으면 `gzip.decompress`.
  `Accept` 헤더는 `application/xml, application/json` 정도로. 테스트는 `Accept-Encoding: gzip`만 본다.
- `ensure_xml`: 앞 공백을 떼고 소문자로 바꾼 뒤 `<!doctype html` 또는 `<html`로 시작하면 `ValueError`. 그 외는 그대로 돌려준다. XML 파싱은 하지 않는다.
- 주소 (eCFR 구축 계획 1-1, 1-2):
  - 목차: `https://www.ecfr.gov/api/versioner/v1/structure/{YYYY-MM-DD}/title-{title}.json`
  - 원문: `https://www.ecfr.gov/api/versioner/v1/full/{YYYY-MM-DD}/title-{title}.xml?part={part}`
  - 날짜는 `as_of.isoformat()`.
- 4xx/5xx는 `urlopen`이 `HTTPError`를 던진다. 잡지 말고 그대로 올려라. 재시도는 이 티켓 범위 밖이다.
- 표준 라이브러리만. 새 패키지 없음. 길이는 50줄 안팎이면 충분하다.
