# SUU-56 feat(db): Dashboard 목록 전체로 회신 PDF 실제 수집 실행

## 목표
저장된 Dashboard 표 HTML에서 canonical_url 목록을 뽑아 `dashboard_letters_collect.collect()`를 실행하는 진입점을 만든다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/4_ADI+CAA/dashboard_letters_run.py` — `run(dashboard_root, letters_root, *, fetch_letter=fetch_letter, today=None) -> dict`
- 이미 있음 (수정 금지): `[2] db/tests/4_ADI+CAA/test_dashboard_letters_run.py`
- 참고만: `adi_letters_run.py`(SUU-54, 완전히 같은 모양), `dashboard_collect.py`(SUU-51, Dashboard run 저장 형태), `adi_dashboard.py`의 `parse_dashboard`(그대로 import), `dashboard_letters_collect.py`(SUU-55, `collect(root, canonical_urls, ...)`, 그대로 import)

## 안 하는 것
- 실제 네트워크로 236건 전체 실행 (이 티켓은 진입점 함수만 만든다. 실행은 사용자가 직접 한다)
- DB 적재, 재시도·429 처리
- `tests/` 아래·`pyproject.toml`·`dashboard_collect.py`·`adi_dashboard.py`·`dashboard_letters_collect.py`·`ecfr_*.py` 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 저장된 Dashboard run(HTML)에서 canonical_url 목록을 뽑아 `dashboard_letters_collect.collect()`를 실행한다 | `test_extracts_canonical_urls_from_saved_dashboard_run_and_collects_letters` |
| canonical_url이 없는 행(파싱 결과 `None`)은 건너뛰고, 중복 없이 정렬된 순서로 요청한다 | `test_skips_rows_without_canonical_url_and_dedupes` |
| 저장된 Dashboard run이 없으면 `FileNotFoundError`를 낸다 | `test_raises_when_no_dashboard_run_found` |

테스트 파일: `[2] db/tests/4_ADI+CAA/test_dashboard_letters_run.py`

## Codex 메모

### `dashboard_letters_run.py`
```python
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Callable

from adi_dashboard import parse_dashboard
from dashboard_letters import fetch_letter
from dashboard_letters_collect import collect as letters_collect


def run(
    dashboard_root: Path,
    letters_root: Path,
    *,
    fetch_letter: Callable[..., dict[str, Any]] = fetch_letter,
    today: date | None = None,
) -> dict[str, Any]:
    dashboard_root = Path(dashboard_root)
    as_of = today or date.today()

    run_path = dashboard_root / "raw" / as_of.isoformat() / "run.json"
    if not run_path.exists():
        raise FileNotFoundError(f"no Dashboard run found for {as_of.isoformat()} in {dashboard_root}")

    dashboard_run = json.loads(run_path.read_text(encoding="utf-8"))
    html_path = dashboard_root / "raw" / as_of.isoformat() / dashboard_run["html_sha256"] / "caa-dashboard.html"
    rows = parse_dashboard(html_path.read_bytes())
    canonical_urls = sorted({row["canonical_url"] for row in rows if row["canonical_url"]})

    return letters_collect(letters_root, canonical_urls, fetch_letter=fetch_letter, today=today)


__all__ = ["run"]
```
- `adi_letters_run.py`(SUU-54)와 완전히 같은 구조다. 차이는 두 가지뿐이다: (1) `dashboard_collect.py`가 저장한 파일 이름은 `caa-dashboard.html`, (2) `canonical_url`이 `None`인 행이 있을 수 있어 필터링한다 (`adi_dashboard.parse_dashboard`가 `www.epa.gov` https 링크가 아니면 `None`을 돌려준다)
- `today`가 없으면 오늘 날짜의 run을 찾는다. 없으면 `FileNotFoundError`
- canonical_url은 `set`으로 중복을 없애고(같은 회신을 여러 행이 가리킬 수 있다) `sorted()`로 순서를 고정한다
- 실제 실행 시 경로: `dashboard_root = [2] db/4) ADI+CAA/caa_dashboard`, `letters_root = [2] db/4) ADI+CAA/caa_dashboard/dashboard_letters` (SUU-55 설계 파일의 저장 위치 절과 동일)

### 흐름
Codex가 `dashboard_letters_run.py` 작성 → `python -m pytest` 초록 → commit·push·PR (제목 = 이 파일 첫 줄 + ` (SUU-56)`) → 사용자 merge
