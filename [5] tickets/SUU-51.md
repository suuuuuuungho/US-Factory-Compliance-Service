# SUU-51 feat(db): CAA Dashboard 표 받아 raw 폴더에 저장

## 목표
CAA Dashboard 페이지를 GET 한 번으로 받아 raw 폴더에 저장하고, 행 수와 Part 63 언급 행 수를 run.json에 남긴다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/4_ADI+CAA/dashboard_fetch.py` — `fetch_dashboard(*, request=None) -> dict`, `DASHBOARD_URL`
- 만들 것: `[2] db/pipeline/4_ADI+CAA/dashboard_collect.py` — `collect(root, *, fetch_dashboard=fetch_dashboard, today=None) -> dict`
- 이미 있음 (수정 금지): `[2] db/tests/4_ADI+CAA/test_dashboard_fetch.py`, `test_dashboard_collect.py`, fixture `adi_dashboard_sample.html`(SUU-47 것 재사용, 실제 236행·Part 63 132행)
- 참고만: `adi_fetch.py`(요청 주입 패턴), `adi_collect.py`(같은 모양의 저장·run.json 진입점, SUU-50), `ecfr_raw.py`(`save_raw`, 그대로 import), `adi_dashboard.py`(`parse_dashboard`, 그대로 import)

## 안 하는 것
- 개별 회신 PDF 받기, ADI 관련 코드, DB 적재, 매주 갱신 스케줄
- 재시도·429 처리
- `tests/` 아래·`pyproject.toml`·`adi_fetch.py`·`adi_collect.py`·`adi_dashboard.py`·`ecfr_*.py` 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 표 HTML이 해시 폴더에 저장되고 manifest.json에 sha256·source_url·byte_size가 남는다 | `test_saves_html_with_manifest_entry` |
| run.json에 `row_count`, `part_63_count`가 남는다 | `test_run_json_has_row_count_and_part_63_count` |
| 표를 찾지 못하면(`parse_dashboard`의 `ValueError`) 그대로 올리고 파일은 저장하지 않는다 | `test_raises_and_does_not_save_when_table_missing` |
| Dashboard는 GET 한 번만 보낸다 (ADI 3단계 폼과 다름) | `test_makes_single_get_request_to_dashboard_url` |
| `fetch_dashboard`가 body·주소·상태·타입·크기를 dict로 돌려준다 | `test_returns_body_and_metadata` |

테스트 파일: `[2] db/tests/4_ADI+CAA/test_dashboard_fetch.py`, `[2] db/tests/4_ADI+CAA/test_dashboard_collect.py`

## Codex 메모

### 1. `dashboard_fetch.py` — GET 한 번
```python
DASHBOARD_URL = (
    "https://www.epa.gov/complying-air-emissions-standards-stationary-sources"
    "/epa-determinations-compliance-and"
)

def fetch_dashboard(*, request=None) -> dict:
    requester = request or _default_requester()
    response = requester(DASHBOARD_URL)  # data=None → GET
    return {
        "body": response.body, "source_url": DASHBOARD_URL,
        "final_url": response.final_url, "http_status": response.http_status,
        "media_type": response.media_type, "byte_size": response.byte_size,
    }
```
- `request(url, data=None)` 규약은 `adi_fetch.py`와 같다: `data=None`이면 GET. 응답 객체는 `.body/.final_url/.http_status/.media_type/.byte_size`
- 테스트의 `Recorder`가 가짜로 넣는다. **네트워크 없음**
- 기본 요청기는 `adi_fetch._default_requester()`와 같은 모양(표준 라이브러리 `urllib`, `User-Agent` 헤더, `timeout=180`)으로 이 파일 안에 새로 작성한다. `adi_fetch.py`는 수정하지 않는다 (내부 함수라 import해서 재사용하지 않는다)

### 2. `dashboard_collect.py` — 저장 + 대조 (SUU-50 `adi_collect.py`와 같은 모양)
```python
def collect(root, *, fetch_dashboard=fetch_dashboard, today=None) -> dict:
    root = Path(root)
    as_of = today or date.today()
    started_at = _now()

    response = fetch_dashboard()
    rows = parse_dashboard(response["body"])  # 표가 없으면 여기서 ValueError. save_raw 호출 전이라 저장 안 됨
    row_count = len(rows)
    part_63_count = sum(
        1 for row in rows if any(s["part"] == "63" for s in row["affected_subparts"])
    )

    entry = save_raw(
        root, as_of, "caa-dashboard.html", response["body"],
        source_url=response["source_url"], final_url=response["final_url"],
        http_status=response["http_status"], media_type=response["media_type"],
    )

    run = {
        "run_id": str(uuid.uuid4()), "dataset": "caa_dashboard", "as_of": as_of.isoformat(),
        "status": "succeeded", "row_count": row_count, "part_63_count": part_63_count,
        "html_sha256": entry["sha256"], "started_at": started_at, "finished_at": _now(),
    }
    _write_run(root, as_of, run)
    return run
```
- **`parse_dashboard`를 `save_raw`보다 먼저 부른다.** 표가 없으면 예외가 파일 저장 전에 나야 완료 기준 3번(저장 안 함)을 만족한다
- `_now()`, `_write_run(root, as_of, run)`은 `adi_collect.py`의 것과 똑같이 이 파일 안에 새로 작성 (import 공유 안 함)
- ADI와 달리 서버가 주는 총건수(hidden 값) 같은 대조 대상이 없어서 `held` 상태가 없다. 파싱이 성공하면 항상 `succeeded`

### 3. 데이터 형태
- `parse_dashboard(html)` 반환: `list[dict]`, 각 행에 `affected_subparts: list[{"part": str, "subpart": str}]` (SUU-47). `part`는 `"63"` 같은 문자열
- `fetch_dashboard()` 반환은 `adi_fetch.fetch_results()`와 같은 6개 키 dict

### 4. 저장 위치
- 실행 진입점: `root = Path(__file__).resolve().parents[2] / "4) ADI+CAA" / "caa_dashboard"` (ADI 진입점이 `.../4) ADI+CAA`를 그대로 쓰는 것과 짝지어, Dashboard는 그 아래 `caa_dashboard/` 하위 폴더를 자기 root로 쓴다)
- 결과: `[2] db/4) ADI+CAA/caa_dashboard/raw/<YYYY-MM-DD>/<sha256>/caa-dashboard.html`, 같은 날짜 폴더에 `manifest.json`, `run.json`

### 5. 흐름
Codex가 `dashboard_fetch.py`, `dashboard_collect.py` 작성 → `python -m pytest` 초록 → commit·push·PR (제목 = 이 파일 첫 줄 + ` (SUU-51)`) → 사용자 merge
