# SUU-54 feat(db): ADI 목록 전체로 회신 PDF 실제 수집 실행

## 목표
저장된 ADI 결과 HTML에서 Control Number 목록을 뽑아 `adi_letters_collect.collect()`를 실행하는 진입점을 만든다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/4_ADI+CAA/adi_letters_run.py` — `run(adi_root, letters_root, *, fetch_letter=fetch_letter, today=None) -> dict`
- 이미 있음 (수정 금지): `[2] db/tests/4_ADI+CAA/test_adi_letters_run.py`
- 참고만: `adi_collect.py`(SUU-50, ADI run 저장 형태), `adi_results.py`의 `parse_results`(그대로 import), `adi_letters_collect.py`(SUU-52, `collect(root, control_numbers, ...)`, 그대로 import)

## 안 하는 것
- 실제 네트워크로 3,825건 전체 실행 (이 티켓은 진입점 함수만 만든다. 실행은 사용자가 직접 한다)
- DB 적재, 재시도·429 처리
- `tests/` 아래·`pyproject.toml`·`adi_collect.py`·`adi_results.py`·`adi_letters_collect.py`·`ecfr_*.py` 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 저장된 ADI run(HTML)에서 Control Number 목록을 뽑아 `adi_letters_collect.collect()`를 실행한다 | `test_extracts_control_numbers_from_saved_adi_run_and_collects_letters` |
| Control Number는 중복 없이, 정해진 순서(정렬)로 한 번씩만 요청한다 | `test_calls_fetch_letter_once_per_unique_control_number_in_sorted_order` |
| 저장된 ADI run이 없으면 `FileNotFoundError`를 낸다 | `test_raises_when_no_adi_run_found` |

테스트 파일: `[2] db/tests/4_ADI+CAA/test_adi_letters_run.py`

## Codex 메모

### `adi_letters_run.py`
```python
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Callable

from adi_letters import fetch_letter
from adi_letters_collect import collect as letters_collect
from adi_results import parse_results


def run(
    adi_root: Path,
    letters_root: Path,
    *,
    fetch_letter: Callable[..., dict[str, Any]] = fetch_letter,
    today: date | None = None,
) -> dict[str, Any]:
    adi_root = Path(adi_root)
    as_of = today or date.today()

    run_path = adi_root / "raw" / as_of.isoformat() / "run.json"
    if not run_path.exists():
        raise FileNotFoundError(f"no ADI run found for {as_of.isoformat()} in {adi_root}")

    adi_run = json.loads(run_path.read_text(encoding="utf-8"))
    html_path = adi_root / "raw" / as_of.isoformat() / adi_run["html_sha256"] / "adi-results.html"
    rows = parse_results(html_path.read_bytes())["rows"]
    control_numbers = sorted({row["control_number"] for row in rows})

    return letters_collect(letters_root, control_numbers, fetch_letter=fetch_letter, today=today)


__all__ = ["run"]
```
- `adi_collect.py`가 남긴 `run.json`의 `html_sha256`으로 저장된 HTML 파일 경로를 그대로 찾는다 (`adi_collect.py`의 `save_raw` 저장 경로 규칙과 동일)
- `today`가 없으면 오늘 날짜의 run을 찾는다. 없으면 `FileNotFoundError`
- Control Number는 `set`으로 중복을 없애고 `sorted()`로 순서를 고정한다 (재현 가능한 실행 순서)
- `adi_run["status"]`가 `held`여도 이 티켓에서는 막지 않는다 (범위 밖 — 필요하면 다음 티켓에서 다룬다)
- 실제 실행 시 경로: `adi_root = [2] db/4) ADI+CAA`, `letters_root = [2] db/4) ADI+CAA/adi_letters` (`adi_collect.py`/`dashboard_collect.py`의 진입점 경로 패턴과 동일)

### 흐름
Codex가 `adi_letters_run.py` 작성 → `python -m pytest` 초록 → commit·push·PR (제목 = 이 파일 첫 줄 + ` (SUU-54)`) → 사용자 merge
