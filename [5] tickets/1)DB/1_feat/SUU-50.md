# SUU-50 feat(db): ADI 전체 목록 받아 raw 폴더에 저장

## 목표
ADI 결과 HTML을 받아 raw 폴더에 저장하고, 서버 총건수·행 수·고유 Control Number 수를 대조해 성공/보류를 run.json에 남긴다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/4_ADI+CAA/adi_collect.py` — `collect(root, *, fetch_results=fetch_results, today=None) -> dict`
- 이미 있음 (수정 금지): `[2] db/tests/4_ADI+CAA/test_adi_collect.py`
- 참고만: `[2] db/pipeline/1_eCFR/ecfr_collect.py`(같은 모양의 수집 진입점), `[2] db/pipeline/1_eCFR/ecfr_raw.py`(`save_raw` 그대로 재사용), `adi_fetch.py`(`fetch_results`), `adi_results.py`(`parse_results`)

## 안 하는 것
- 상세(Abstract)·PDF 받기, Dashboard 수집, DB 적재
- 분류별 분할 수집 — `fetch_results()`를 기본값(`category="ALL"`)으로 한 번만 호출
- 재시도·429 처리, `raw/adi/` 폴더 재대조(갱신 티켓의 일)
- `tests/` 아래·`pyproject.toml`·`adi_fetch.py`·`adi_results.py`·`ecfr_*.py` 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 결과 HTML이 해시 폴더에 저장되고 manifest.json에 sha256·source_url·byte_size가 남는다 | `test_saves_html_with_manifest_entry` |
| run.json에 `results_length`, `row_count`, `unique_control_numbers`가 남고 셋이 같으면 `succeeded` | `test_succeeds_when_counts_all_match` |
| 총건수 ≠ 행 수면 `held`, 이유는 `results_length_mismatch`, 파일은 지우지 않는다 | `test_holds_when_results_length_differs_from_row_count` |
| Control Number 중복이 있으면 `held`, 이유는 `duplicate_control_number` | `test_holds_when_control_numbers_duplicate` |

테스트 파일: `[2] db/tests/4_ADI+CAA/test_adi_collect.py`

## Codex 메모

### 1. 전체 흐름 (eCFR `collect`와 같은 모양)
```python
def collect(root, *, fetch_results=fetch_results, today=None) -> dict:
    root = Path(root)
    as_of = today or date.today()
    started_at = _now()
    response = fetch_results()  # category 기본값 ALL, 인자 없이 호출
    parsed = parse_results(response["body"])
    rows = parsed["rows"]
    row_count = len(rows)
    unique_control_numbers = len({r["control_number"] for r in rows})

    entry = save_raw(
        root, as_of, "adi-results.html", response["body"],
        source_url=response["source_url"], final_url=response["final_url"],
        http_status=response["http_status"], media_type=response["media_type"],
    )

    if parsed["results_length"] != row_count:
        status, reason = "held", "results_length_mismatch"
    elif row_count != unique_control_numbers:
        status, reason = "held", "duplicate_control_number"
    else:
        status, reason = "succeeded", None

    run = {
        "run_id": str(uuid.uuid4()), "dataset": "adi", "as_of": as_of.isoformat(),
        "status": status, "reason": reason,
        "results_length": parsed["results_length"], "row_count": row_count,
        "unique_control_numbers": unique_control_numbers,
        "html_sha256": entry["sha256"],
        "started_at": started_at, "finished_at": _now(),
    }
    _write_run(root, as_of, run)  # root / "raw" / as_of.isoformat() / "run.json"
    return run
```
- `save_raw`는 `[2] db/pipeline/1_eCFR/ecfr_raw.py`에서 그대로 import한다 (새로 만들지 않는다). `pyproject.toml`의 `pythonpath`에 `1_eCFR`, `4_ADI+CAA` 폴더가 둘 다 있어 바로 `from ecfr_raw import save_raw`가 된다
- `today` 인자는 테스트가 날짜를 고정하려고 주입한다. 기본은 `date.today()`
- `_now()`, `_write_run()`은 `ecfr_collect.py`의 것과 같은 모양으로 새로 작성 (import 공유 안 함, 각 모듈 독립)

### 2. 데이터 형태
- `fetch_results()` 반환: `{"body": bytes, "source_url": str, "final_url": str, "http_status": int, "media_type": str, "byte_size": int}` (SUU-49)
- `parse_results(body)` 반환: `{"results_length": int, "rows": [{"control_number": str, ...}, ...]}` (SUU-48)
- 저장 파일 이름은 `adi-results.html` 하나로 고정 (분류별 분할이 없으므로 파일도 하나)

### 3. 저장 위치
- 실행 진입점(`if __name__ == "__main__":`)은 `root = Path(__file__).resolve().parents[2] / "4) ADI+CAA"` (eCFR과 같은 패턴, 괄호 있는 폴더명)
- 결과: `[2] db/4) ADI+CAA/raw/<YYYY-MM-DD>/<sha256>/adi-results.html`, 같은 날짜 폴더에 `manifest.json`, `run.json`

### 4. 흐름
Codex가 `adi_collect.py` 작성 → `python -m pytest` 초록 → commit·push·PR (제목 = 이 파일 첫 줄 + ` (SUU-50)`) → 사용자 merge

### 5. 참고: 이전 SUU-50과 번호 충돌
- 예전에 존재했던 다른 SUU-50(폴더 구조 정리, PR #28로 이미 merge됨)의 설계 파일은 이번 브랜치에서 `[5] tickets/SUU-50_folder_cleanup.md`로 이름을 바꿨다. Linear에서 그 이슈가 삭제되고 번호가 이번 티켓에 재사용됐다.
