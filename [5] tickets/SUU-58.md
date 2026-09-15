# SUU-58 feat(db): ADI 목록 전체로 상세 메타데이터 실제 수집 실행

## 목표
저장된 ADI 결과 HTML에서 Control Number 목록을 뽑아 `adi_details_collect.collect()`를 실행하는 진입점을 만든다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/4_ADI+CAA/adi_details_run.py` — `run(adi_root, details_root, *, fetch_details=fetch_details, today=None) -> dict`
- 이미 있음 (수정 금지): `[2] db/tests/4_ADI+CAA/test_adi_details_run.py`
- 참고만: `adi_collect.py`(SUU-50, ADI run·manifest 저장 형태), `adi_results.py`의 `parse_results`(그대로 import), `adi_details_collect.py`(SUU-57, `collect(root, results_html, results_source_url, control_numbers, ...)`, 그대로 import), `adi_letters_run.py`(SUU-54, 거의 같은 모양의 이미 완료된 진입점)

## 안 하는 것
- 실제 네트워크로 3,825건 전체 실행 (이 티켓은 진입점 함수만 만든다. 실행은 사용자가 직접 한다)
- DB 적재, 재시도
- `tests/` 아래·`pyproject.toml`·`adi_collect.py`·`adi_results.py`·`adi_details_collect.py`·`adi_letters_run.py` 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 저장된 최신 ADI run에서 Control Number 목록을 뽑는다 | `test_extracts_control_numbers_from_saved_adi_run_and_collects_details` |
| 뽑은 목록으로 `adi_details_collect.collect()`를 호출한다 (Control Number는 중복 없이 정렬된 순서로) | `test_calls_fetch_details_with_sorted_unique_control_numbers` |
| 저장된 ADI run이 없으면 명확한 에러(`FileNotFoundError`)를 낸다 | `test_raises_when_no_adi_run_found` |

테스트 파일: `[2] db/tests/4_ADI+CAA/test_adi_details_run.py`

## Codex 메모

### `adi_details_run.py`
```python
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Callable

from adi_details import fetch_details
from adi_details_collect import collect as details_collect
from adi_results import parse_results


def run(
    adi_root: Path,
    details_root: Path,
    *,
    fetch_details: Callable[..., dict[str, Any]] = fetch_details,
    today: date | None = None,
) -> dict[str, Any]:
    adi_root = Path(adi_root)
    as_of = today or date.today()

    run_dir = adi_root / "raw" / as_of.isoformat()
    run_path = run_dir / "run.json"
    if not run_path.exists():
        raise FileNotFoundError(f"no ADI run found for {as_of.isoformat()} in {adi_root}")

    adi_run = json.loads(run_path.read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    entry = next(e for e in manifest if e["sha256"] == adi_run["html_sha256"])

    html_path = run_dir / adi_run["html_sha256"] / "adi-results.html"
    results_html = html_path.read_bytes()
    rows = parse_results(results_html)["rows"]
    control_numbers = sorted({row["control_number"] for row in rows})

    return details_collect(
        details_root,
        results_html,
        entry["final_url"],
        control_numbers,
        fetch_details=fetch_details,
        today=today,
    )


__all__ = ["run"]
```
- `adi_collect.py`가 남긴 `run.json`의 `html_sha256`으로 저장된 HTML 파일 경로를 그대로 찾는다 (`adi_letters_run.py`와 동일한 방식)
- `results_source_url`은 같은 폴더의 `manifest.json`에서 `sha256`이 일치하는 항목의 `final_url`을 쓴다 — `adi_details.py`의 `fetch_details`가 이 URL을 기준으로 폼 action을 `urljoin`한다 (`adi_details_collect.py` 테스트의 `RESULTS_SOURCE_URL` 인자와 같은 역할)
- `today`가 없으면 오늘 날짜의 run을 찾는다. 없으면 `FileNotFoundError`
- Control Number는 `set`으로 중복을 없애고 `sorted()`로 순서를 고정한다 (재현 가능한 실행 순서)
- 실제 실행 시 경로: `adi_root = [2] db/4) ADI+CAA`, `details_root = [2] db/4) ADI+CAA/adi_details` (기존 진입점 경로 패턴과 동일)

### 흐름
Codex가 `adi_details_run.py` 작성 → `python -m pytest` 초록 → commit·push·PR (제목 = 이 파일 첫 줄 + ` (SUU-58)`) → 사용자 merge
