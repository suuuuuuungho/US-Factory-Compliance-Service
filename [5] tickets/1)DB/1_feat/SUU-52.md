# SUU-52 feat(db): ADI 회신 원문 PDF를 해시 폴더에 저장

## 목표
Control Number 목록을 받아 각 회신 원문을 받아오고, 매직바이트로 PDF만 골라 해시 폴더에 저장하며 성공/실패를 run.json에 남긴다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/4_ADI+CAA/adi_letters.py` — `fetch_letter(control_number, *, request=None) -> dict`, `FILE_URL`
- 만들 것: `[2] db/pipeline/4_ADI+CAA/adi_letters_collect.py` — `collect(root, control_numbers, *, fetch_letter=fetch_letter, today=None) -> dict`
- 이미 있음 (수정 금지): `[2] db/tests/4_ADI+CAA/test_adi_letters.py`, `test_adi_letters_collect.py`
- 참고만: `adi_fetch.py`(요청 주입·기본 요청기 패턴), `adi_collect.py`·`dashboard_collect.py`(같은 모양의 저장·run.json 진입점), `ecfr_raw.py`(`save_raw`, 그대로 import), `adi_results.py`의 `_FILE_URL`(같은 주소 패턴, private이라 import하지 않고 이 파일에 새로 둔다)

## 안 하는 것
- SUU-50 결과 HTML에서 Control Number 목록을 자동으로 뽑아 전체 3,825건 실행 (다음 실행 티켓의 일). 이 티켓은 `collect(root, control_numbers, ...)`처럼 목록을 인자로 받는다
- 상세 Abstract·Title 등 메타데이터 수집, 재시도·429 처리
- 텍스트·HTML 형식 원문 저장 (PDF 아니면 저장하지 않고 실패로만 기록)
- `tests/` 아래·`pyproject.toml`·`adi_fetch.py`·`adi_collect.py`·`adi_results.py`·`ecfr_*.py` 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 원문을 받아 매직바이트(`%PDF`)를 확인하고, PDF면 해시 폴더에 `<control_number>.pdf`로 저장 (manifest.json에 sha256 포함) | `test_saves_pdf_and_manifest_entry_for_one_control_number` |
| Content-Type이 pdf라 해도 매직바이트가 아니면 `is_pdf=False` | `test_flags_false_when_body_is_not_pdf_even_if_content_type_says_pdf` |
| 원문 주소는 `FILE_URL + control_number` | `test_requests_the_file_contents_endpoint_for_the_control_number` |
| PDF가 아니면 저장하지 않고 실패 목록에 `reason="not_pdf"`로 남긴다 | `test_marks_not_pdf_without_saving` |
| 여러 건을 처리하면 run.json에 `requested`/`succeeded`/`failed`/`failure_reasons`가 남는다 | `test_records_success_and_failure_counts_for_multiple_control_numbers` |
| 받아오다 예외가 나면 전체가 멈추지 않고 `reason="fetch_error"`로 실패에 남긴다 | `test_fetch_error_is_recorded_as_failure_not_raised` |

테스트 파일: `[2] db/tests/4_ADI+CAA/test_adi_letters.py`, `[2] db/tests/4_ADI+CAA/test_adi_letters_collect.py`

## Codex 메모

### 1. `adi_letters.py` — 한 건 받기 + PDF 판별
```python
FILE_URL = "https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id="

def fetch_letter(control_number: str, *, request=None) -> dict:
    requester = request or _default_requester()
    url = FILE_URL + control_number
    response = requester(url)  # data=None → GET
    is_pdf = response.body.lstrip()[:4] == b"%PDF"
    return {
        "control_number": control_number, "body": response.body,
        "source_url": url, "final_url": response.final_url,
        "http_status": response.http_status, "media_type": response.media_type,
        "byte_size": response.byte_size, "is_pdf": is_pdf,
    }
```
- **매직바이트가 최종 판단이다.** `.cfm` 주소는 Content-Type이 실제 내용과 다를 수 있다 (계획 문서 1-3절). `media_type`은 참고용으로만 dict에 남기고 판별에 쓰지 않는다
- 기본 요청기는 `adi_fetch.py`의 `_default_requester()`와 같은 모양(표준 라이브러리 `urllib`, `User-Agent`, `timeout=180`)으로 이 파일 안에 새로 작성한다. `adi_fetch.py`는 수정하지 않는다
- `request(url, data=None)` 규약은 기존 파일들과 같다. 테스트는 `request`를 가짜로 주입해 호출 주소만 검사한다

### 2. `adi_letters_collect.py` — 여러 건 처리 + 저장 + 집계
```python
def collect(root, control_numbers, *, fetch_letter=fetch_letter, today=None) -> dict:
    root = Path(root)
    as_of = today or date.today()
    started_at = _now()

    successes, failures = [], []
    for control_number in control_numbers:
        try:
            letter = fetch_letter(control_number)
        except Exception as error:
            failures.append({"control_number": control_number, "reason": "fetch_error", "detail": str(error)})
            continue
        if not letter["is_pdf"]:
            failures.append({"control_number": control_number, "reason": "not_pdf"})
            continue
        entry = save_raw(
            root, as_of, f"{control_number}.pdf", letter["body"],
            source_url=letter["source_url"], final_url=letter["final_url"],
            http_status=letter["http_status"], media_type=letter["media_type"],
        )
        successes.append({"control_number": control_number, "sha256": entry["sha256"], "path": entry["path"]})

    failure_reasons: dict[str, int] = {}
    for failure in failures:
        failure_reasons[failure["reason"]] = failure_reasons.get(failure["reason"], 0) + 1

    run = {
        "run_id": str(uuid.uuid4()), "dataset": "adi_letters", "as_of": as_of.isoformat(),
        "requested": len(control_numbers), "succeeded": len(successes), "failed": len(failures),
        "failure_reasons": failure_reasons, "failures": failures,
        "started_at": started_at, "finished_at": _now(),
    }
    _write_run(root, as_of, run)
    return run
```
- **하나가 실패해도 나머지는 계속 처리한다.** `fetch_letter`가 예외를 던지면 그 건만 `fetch_error`로 기록하고 다음 건으로 넘어간다 (테스트: `test_fetch_error_is_recorded_as_failure_not_raised`)
- `control_numbers`는 `list[str]` (제너레이터 아님 — `len()`을 그대로 쓴다)
- 실패만 있으면(성공 0건) `manifest.json`이 아예 생기지 않을 수 있다 (`save_raw`가 한 번도 안 불림). 테스트가 이를 확인한다
- `_now()`, `_write_run(root, as_of, run)`은 `adi_collect.py`/`dashboard_collect.py`와 같은 모양으로 이 파일 안에 새로 작성

### 3. 저장 위치
- 실행 진입점은 아직 만들지 않는다 (`__main__` 불필요). 다음 실행 티켓에서 SUU-50 목록 + 이 `collect`를 이어 붙인다
- 테스트는 `pytest tmp_path`를 `root`로 쓴다. 실제 실행 시 저장 경로는 `[2] db/4) ADI+CAA/adi_letters/raw/<YYYY-MM-DD>/<sha256>/<control_number>.pdf` 형태가 될 예정 (다음 티켓에서 진입점의 `root`를 정한다)

### 4. 흐름
Codex가 `adi_letters.py`, `adi_letters_collect.py` 작성 → `python -m pytest` 초록 → commit·push·PR (제목 = 이 파일 첫 줄 + ` (SUU-52)`) → 사용자 merge
