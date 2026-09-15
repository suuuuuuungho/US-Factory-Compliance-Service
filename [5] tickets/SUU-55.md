# SUU-55 feat(db): CAA Dashboard 회신 원문 PDF를 해시 폴더에 저장

## 목표
canonical_url 목록을 받아 각 회신 원문을 받아오고, 매직바이트로 PDF만 골라 해시 폴더에 저장하며 성공/실패를 run.json에 남긴다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/4_ADI+CAA/dashboard_letters.py` — `fetch_letter(canonical_url, *, request=None) -> dict`
- 만들 것: `[2] db/pipeline/4_ADI+CAA/dashboard_letters_collect.py` — `collect(root, canonical_urls, *, fetch_letter=fetch_letter, today=None) -> dict`
- 이미 있음 (수정 금지): `[2] db/tests/4_ADI+CAA/test_dashboard_letters.py`, `test_dashboard_letters_collect.py`
- 참고만: `adi_letters.py`·`adi_letters_collect.py`(SUU-52, 완전히 같은 모양. Control Number 대신 canonical_url을 쓴다는 점만 다르다), `ecfr_raw.py`(`save_raw`, 그대로 import)

## 안 하는 것
- SUU-51 저장된 Dashboard HTML에서 canonical_url 목록을 자동으로 뽑아 실행하는 진입점 (다음 실행 티켓, SUU-54와 같은 패턴)
- 상세 메타데이터 수집, 재시도·429 처리
- 텍스트·HTML 형식 원문 저장 (PDF 아니면 저장하지 않고 실패로만 기록)
- `tests/` 아래·`pyproject.toml`·`adi_letters.py`·`adi_letters_collect.py`·`adi_dashboard.py`·`ecfr_*.py` 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 원문을 받아 매직바이트(`%PDF`)를 확인하고, PDF면 해시 폴더에 `<sha256(canonical_url)>.pdf`로 저장 (manifest.json에 sha256 포함) | `test_saves_pdf_and_manifest_entry_for_one_canonical_url` |
| Content-Type이 pdf라 해도 매직바이트가 아니면 `is_pdf=False` | `test_flags_false_when_body_is_not_pdf_even_if_content_type_says_pdf` |
| 원문 주소는 canonical_url 그대로 요청한다 | `test_requests_the_canonical_url_directly` |
| PDF가 아니면 저장하지 않고 실패 목록에 `reason="not_pdf"`로 남긴다 | `test_marks_not_pdf_without_saving` |
| 여러 건을 처리하면 run.json에 `requested`/`succeeded`/`failed`/`failure_reasons`가 남는다 | `test_records_success_and_failure_counts_for_multiple_urls` |
| 받아오다 예외가 나면 전체가 멈추지 않고 `reason="fetch_error"`로 실패에 남긴다 | `test_fetch_error_is_recorded_as_failure_not_raised` |

테스트 파일: `[2] db/tests/4_ADI+CAA/test_dashboard_letters.py`, `[2] db/tests/4_ADI+CAA/test_dashboard_letters_collect.py`

## Codex 메모

### 1. `dashboard_letters.py` — 한 건 받기 + PDF 판별
```python
def fetch_letter(canonical_url: str, *, request=None) -> dict:
    requester = request or _default_requester()
    response = requester(canonical_url)  # data=None → GET
    is_pdf = response.body.lstrip()[:4] == b"%PDF"
    return {
        "canonical_url": canonical_url, "body": response.body,
        "source_url": canonical_url, "final_url": response.final_url,
        "http_status": response.http_status, "media_type": response.media_type,
        "byte_size": response.byte_size, "is_pdf": is_pdf,
    }
```
- `adi_letters.py`의 `fetch_letter`와 완전히 같은 구조다. 차이는 주소를 조립하지 않고 canonical_url을 그대로 쓴다는 점뿐이다
- 기본 요청기는 `adi_fetch.py`의 `_default_requester()`와 같은 모양(표준 라이브러리 `urllib`, `User-Agent`, `timeout=180`)으로 이 파일 안에 새로 작성한다. 기존 파일은 수정하지 않는다
- **매직바이트가 최종 판단이다.** `media_type`은 참고용으로만 dict에 남기고 판별에 쓰지 않는다

### 2. `dashboard_letters_collect.py` — 여러 건 처리 + 저장 + 집계
```python
def collect(root, canonical_urls, *, fetch_letter=fetch_letter, today=None) -> dict:
    root = Path(root)
    as_of = today or date.today()
    started_at = _now()

    successes, failures = [], []
    for canonical_url in canonical_urls:
        try:
            letter = fetch_letter(canonical_url)
        except Exception as error:
            failures.append({"canonical_url": canonical_url, "reason": "fetch_error", "detail": str(error)})
            continue
        if not letter["is_pdf"]:
            failures.append({"canonical_url": canonical_url, "reason": "not_pdf"})
            continue
        name = f"{hashlib.sha256(canonical_url.encode()).hexdigest()}.pdf"
        entry = save_raw(
            root, as_of, name, letter["body"],
            source_url=letter["source_url"], final_url=letter["final_url"],
            http_status=letter["http_status"], media_type=letter["media_type"],
        )
        successes.append({"canonical_url": canonical_url, "sha256": entry["sha256"], "path": entry["path"]})

    failure_reasons: dict[str, int] = {}
    for failure in failures:
        failure_reasons[failure["reason"]] = failure_reasons.get(failure["reason"], 0) + 1

    run = {
        "run_id": str(uuid.uuid4()), "dataset": "caa_dashboard_letters", "as_of": as_of.isoformat(),
        "requested": len(canonical_urls), "succeeded": len(successes), "failed": len(failures),
        "failure_reasons": failure_reasons, "failures": failures,
        "started_at": started_at, "finished_at": _now(),
    }
    _write_run(root, as_of, run)
    return run
```
- **파일 이름은 canonical_url의 sha256이다.** Dashboard에는 Control Number 같은 원본 식별자가 없다 (계획 문서 3-1절: "원본 ID가 없는 Dashboard는 처음 발견한 정규화 문서 URL에 내부 source_key를 부여한다"). facility_name 등은 파일시스템에 안전하지 않을 수 있어 쓰지 않는다
- **하나가 실패해도 나머지는 계속 처리한다.** `adi_letters_collect.py`와 동일한 에러 격리
- `canonical_urls`는 `list[str]` (`len()`을 그대로 쓴다)
- 실패만 있으면(성공 0건) `manifest.json`이 아예 생기지 않을 수 있다
- `_now()`, `_write_run(root, as_of, run)`은 기존 `*_collect.py` 파일들과 같은 모양으로 이 파일 안에 새로 작성

### 3. 저장 위치
- 실행 진입점은 아직 만들지 않는다. 다음 실행 티켓에서 SUU-51의 Dashboard HTML에서 canonical_url 목록을 뽑아 이어 붙인다 (SUU-54 패턴과 동일)
- 테스트는 `pytest tmp_path`를 `root`로 쓴다. 실제 실행 시 저장 경로는 `[2] db/4) ADI+CAA/caa_dashboard/dashboard_letters/raw/<YYYY-MM-DD>/<sha256>/<sha256(canonical_url)>.pdf` 형태가 될 예정 (다음 티켓에서 진입점의 `root`를 정한다)

### 4. 흐름
Codex가 `dashboard_letters.py`, `dashboard_letters_collect.py` 작성 → `python -m pytest` 초록 → commit·push·PR (제목 = 이 파일 첫 줄 + ` (SUU-55)`) → 사용자 merge
