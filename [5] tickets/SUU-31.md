# SUU-31 feat(db): eCFR 제목 API에서 Title 40 반영 기준일 읽기

## 목표
titles.json에서 Title 40의 반영 완료일·변경일과 "정부 작업 중" 여부를 읽어 돌려준다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/1_eCFR/ecfr_titles.py` (이 파일 하나)
- 이미 있음 (수정 금지): `[2] db/tests/test_ecfr_titles.py`, `[2] db/tests/fixtures/ecfr_titles.json`, `pyproject.toml`

## 안 하는 것
- XML·목차·이력 다운로드, DB 저장, 스케줄링
- `fetch_titles`의 네트워크 테스트
- `tests/` 아래 파일 수정
- 새 의존성 추가 (표준 라이브러리만)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| Title 40의 up_to_date_as_of, latest_amended_on, latest_issue_date, import_in_progress를 돌려준다 | `test_parses_title_40_dates_and_flag` |
| import_in_progress가 true면 결과에 True로 표시된다 | `test_keeps_import_in_progress_true` |
| Title 40이 없으면 ValueError | `test_raises_when_title_missing` |

## Codex 메모

**모듈 이름**: `ecfr_titles` (파일 `ecfr_titles.py`). `pyproject.toml`이 `[2] db/pipeline/1_eCFR`을 pythonpath에 넣어두었으니 `from ecfr_titles import parse_title_status`로 import 된다. 폴더 이름이 숫자로 시작해서 패키지 import는 안 된다 — 그래서 `ecfr_` 접두어를 쓴다.

**만들 것 2개**

```python
@dataclass(frozen=True)
class TitleStatus:
    up_to_date_as_of: date      # 반영 완료 기준일. 이 날짜를 XML 기준일로 쓴다
    latest_amended_on: date     # 실질 변경일
    latest_issue_date: date     # 발행 변경일
    import_in_progress: bool    # True면 정부가 반영 작업 중 → 수집 보류

def parse_title_status(titles_json: dict, title: int = 40) -> TitleStatus: ...
def fetch_titles(url: str = "https://www.ecfr.gov/api/versioner/v1/titles.json") -> dict: ...
```

**입력 JSON 모양** (샘플 `tests/fixtures/ecfr_titles.json`, 실제 응답)
```json
{
  "titles": [ {"number": 40, "name": "Protection of Environment",
               "latest_amended_on": "2026-09-09", "latest_issue_date": "2026-09-09",
               "up_to_date_as_of": "2026-09-10", "reserved": false}, ... ],
  "meta": {"date": "2026-09-10", "import_in_progress": false}
}
```
- 날짜 3개는 `titles[]` 안의 해당 title에 있고, `import_in_progress`는 **최상위 `meta`** 에 있다 (title별이 아님).
- 날짜 문자열은 `date.fromisoformat`으로 `datetime.date`로 바꾼다. 테스트가 `date` 객체와 비교한다.
- `title`이 목록에 없으면 `ValueError`. 메시지에 번호(`40`)를 넣는다 — 테스트가 `match="40"`으로 본다.

**fetch_titles**: `urllib.request`로 GET. 헤더 `Accept: application/json`, `Accept-Encoding: gzip`. 응답 헤더 `Content-Encoding`이 gzip이면 `gzip.decompress` 후 `json.loads`. (계획서: gzip 헤더 없으면 HTTP 406이 난 적 있음.) 테스트 없음 — 짧게.

**PC의 오늘 날짜를 어디에도 쓰지 않는다.** 기준일은 오직 응답에서 나온다.
