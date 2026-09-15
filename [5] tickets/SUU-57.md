# SUU-57 feat(db): ADI 상세 메타데이터(Abstract 등) 배치로 가져오기

## 목표
저장된 ADI 결과 HTML의 hidden 필드를 재사용해 여러 Control Number를 한 번에(체크박스 재제출) 요청하고, 응답에서 Author/Categories/Office/Abstract를 파싱해 저장한다.

## 배경 (실제 사이트에서 직접 확인)
ADI의 "View Details" 버튼은 별도 상세 페이지가 아니다. 결과 목록 폼(`this_form`, hidden `fuseaction=home.dsp_show_results`)을 체크된 `control_number` 값들과 함께 그대로 재제출하는 방식이다. 실제 M200005/1800013으로 확인:
- 결과 목록 HTML 자체가 이미 재제출에 필요한 hidden 필드를 전부 담고 있다 (`adi_results_sample.html`도 마찬가지).
- 응답 HTML에 `Author`, `Categories`, `Office`, `Abstract`(Q/A 전문)가 포함된다.
- 여러 control_number를 한 번에 체크(`control_number` 필드를 반복)해서 보내면 batch로 여러 행이 한 응답에 온다.
- `determination`/`downloadList` 필드를 채우는 건 틀렸다 (`"The search returned zero determinations."`). 실제 checkbox 필드인 `control_number`(반복 가능)를 채워야 한다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/4_ADI+CAA/adi_details.py` — `fetch_details(results_html, results_source_url, control_numbers, *, request=None) -> dict`
- 만들 것: `[2] db/pipeline/4_ADI+CAA/adi_details_parse.py` — `parse_details(html: bytes) -> list[dict]`
- 만들 것: `[2] db/pipeline/4_ADI+CAA/adi_details_collect.py` — `collect(root, results_html, results_source_url, control_numbers, *, fetch_details=fetch_details, today=None, chunk_size=100) -> dict`
- 이미 있음 (수정 금지): `test_adi_details.py`, `test_adi_details_parse.py`, `test_adi_details_collect.py`
- 새 fixture (이미 있음, 실제 응답 캡처): `[2] db/tests/4_ADI+CAA/fixtures/adi_details_response_single.html`, `adi_details_response_batch.html`
- 참고만: `adi_fetch.py`의 `_form`(그대로 import, hidden 필드 추출용) · `_default_requester` 패턴, `adi_results.py`(`parse_results`, lxml 스타일 참고), `adi_collect.py`(`_now`/`_write_run` 패턴), `dashboard_letters_collect.py`(청크 없이 단건 루프의 에러 격리 패턴 참고 — 이번엔 청크 단위)

## 안 하는 것
- 저장된 ADI run(SUU-48/adi_collect.py)에서 control_number 전체 목록을 자동으로 뽑아 실행하는 진입점 (다음 실행 티켓, SUU-56 패턴과 동일)
- 실제 3,825건 전체 실행
- PDF/원문 저장 (SUU-52에서 이미 처리)
- CFR 인용 파싱, eCFR 연결 (Step 2 영역, 범위 밖)
- `tests/` 아래·`pyproject.toml`·`adi_fetch.py`·`adi_results.py`·`adi_collect.py`·`adi_letters*.py`·`dashboard_*.py`·`ecfr_*.py` 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 저장된 결과 HTML의 hidden 필드를 재사용해 체크된 control_number들과 함께 결과 폼을 재제출한다 | `test_resubmits_results_form_with_checked_control_numbers` (`test_adi_details.py`) |
| 응답을 다른 fetch_* 함수들과 같은 형태(dict: body/source_url/final_url/http_status/media_type/byte_size)로 돌려준다 | `test_returns_response_envelope_with_body_and_metadata` |
| control_number 목록이 비어 있으면 네트워크 요청을 하지 않는다 | `test_no_network_request_for_empty_control_number_list` |
| 실제 캡처한 단건 응답에서 7개 필드(control_number/title/letter_date_raw/author/categories/office/abstract)를 정확히 뽑는다 | `test_parses_single_real_detail_response` (`test_adi_details_parse.py`) |
| batch 응답에서는 여러 행을 순서대로 뽑는다 | `test_parses_multiple_rows_from_batch_response_in_order` |
| 결과가 0건("zero determinations")이면 빈 리스트를 돌려준다 | `test_zero_determinations_response_returns_empty_list` |
| chunk_size보다 적으면 한 번만 요청해서 전부 처리한다 | `test_collects_all_rows_in_one_chunk_when_under_chunk_size` (`test_adi_details_collect.py`) |
| chunk_size 단위로 나눠 여러 번 요청한다 | `test_splits_into_chunks_of_chunk_size` |
| 청크 하나가 실패해도(예외) 나머지 청크는 계속 처리하고 실패를 기록한다 | `test_one_failing_chunk_does_not_abort_the_rest` |
| run.json이 실제로 저장되고 반환값과 일치한다 | `test_run_json_is_written_and_matches_returned_dict` |

테스트 파일: `[2] db/tests/4_ADI+CAA/test_adi_details.py`, `test_adi_details_parse.py`, `test_adi_details_collect.py`

## Codex 메모

### 1. `adi_details.py` — 재제출
```python
from adi_fetch import _form, _default_requester  # 그대로 재사용

def fetch_details(results_html, results_source_url, control_numbers, *, request=None):
    if not control_numbers:
        return {"body": b"", "source_url": results_source_url, "final_url": results_source_url,
                "http_status": None, "media_type": "", "byte_size": 0}
    requester = request or _default_requester()
    action, hidden = _form(results_html, "home.dsp_show_results")
    fields = list(hidden) + [("control_number", cn) for cn in control_numbers]
    url = urljoin(results_source_url, action)
    response = requester(url, fields)
    return {
        "body": response.body, "source_url": url, "final_url": response.final_url,
        "http_status": response.http_status, "media_type": response.media_type,
        "byte_size": response.byte_size,
    }
```
- `_form(html, fuseaction)`은 `adi_fetch.py`에 이미 있다. `home.dsp_show_results` fuseaction의 hidden input들을 전부 찾아준다 — 결과 목록 페이지 자체가 이 폼이다.
- `_default_requester`는 `adi_fetch.py`에 있는 것을 그대로 쓰거나(있으면 import), 없으면 `adi_letters.py` 스타일로 이 파일 안에 새로 작성해도 된다. 기존 파일은 수정하지 않는다.
- 빈 리스트일 때 네트워크를 타지 않는 이유: `collect()`가 청크를 순회하다 마지막 청크가 빌 수 있는 경우를 방지.

### 2. `adi_details_parse.py` — 파싱
- 행 구분: `<tr class="no-sort">` 안의 `<td>` 블록. 결과 0건이면 "The search returned zero determinations." 텍스트만 있고 `tr.no-sort`가 없다 — 이때 빈 리스트.
- 각 행 첫 `div`(`font-size: 1.1em`): `<input name="control_number" type="checkbox" value="M200005">&nbsp;<A ...>제목</A>&nbsp;(M200005)&nbsp;04/08/2020` — control_number는 checkbox의 `value`, title은 `<A>` 텍스트, letter_date_raw는 마지막 `&nbsp;` 뒤 날짜.
- 두 번째 `div`(`font-size: 0.9em`, Abstract 앞): `<strong>Author</strong>:&nbsp;Sara Breneman&nbsp;<strong>Categories</strong>:&nbsp;MACT, NESHAP&nbsp;<strong>Office</strong>:&nbsp;Region 5` — 라벨 텍스트를 기준으로 정규식이나 문자열 분리로 세 값을 뽑는다. categories는 콤마로 split.
- 그 다음 `<strong>Abstract</strong>:` div 바로 다음 형제 `div`의 텍스트가 abstract 전문(Q/A 포함, `<br>`는 줄바꿈이나 공백으로).
- `lxml.html`을 쓴다 (`adi_results.py`와 같은 라이브러리, 이미 의존성에 있음).
- 실제 응답 예시가 fixture 2개에 그대로 있다 — 정확한 문자열은 그 fixture와 테스트 assert를 참고.

### 3. `adi_details_collect.py` — 청크 처리 + 저장
```python
def collect(root, results_html, results_source_url, control_numbers, *,
            fetch_details=fetch_details, today=None, chunk_size=100):
    root = Path(root)
    as_of = today or date.today()
    started_at = _now()

    rows, failures = [], []
    for start in range(0, len(control_numbers), chunk_size):
        chunk = control_numbers[start:start + chunk_size]
        try:
            response = fetch_details(results_html, results_source_url, chunk)
        except Exception as error:
            failures.append({"control_numbers": chunk, "reason": "fetch_error", "detail": str(error)})
            continue
        rows.extend(parse_details(response["body"]))

    (root / "raw" / as_of.isoformat()).mkdir(parents=True, exist_ok=True)
    (root / "raw" / as_of.isoformat() / "details.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    run = {
        "run_id": str(uuid.uuid4()), "dataset": "adi_details", "as_of": as_of.isoformat(),
        "requested": len(control_numbers), "succeeded": len(rows),
        "failed": sum(len(f["control_numbers"]) for f in failures),
        "failures": failures, "started_at": started_at, "finished_at": _now(),
    }
    _write_run(root, as_of, run)
    return run
```
- `fetch_details`는 SUU-57에서 만든 함수를 기본값으로 주입받는다 (테스트는 가짜로 대체).
- `parse_details`는 위 2번 함수를 그대로 import.
- 실패는 **청크 단위**다 (letters처럼 건별이 아니다) — 한 번의 HTTP 요청이 여러 control_number를 담기 때문. `failures`의 각 항목은 `control_numbers`(그 청크 전체) 리스트를 담는다.
- `_now()`, `_write_run(root, as_of, run)`은 `adi_collect.py`와 같은 모양으로 이 파일 안에 새로 작성.
- `details.json`은 매 실행마다 덮어쓴다 (같은 `as_of`를 다시 실행하면 새로 씀). manifest/해시 저장은 하지 않는다 — 원문 파일이 아니라 파싱된 구조화 데이터이기 때문 (PDF 저장은 SUU-52가 이미 처리).

### 4. 실행 시 참고 (이번 티켓 범위 아님, 다음 실행 티켓용 메모)
- 실제 실행 시 `results_html`/`results_source_url`은 `adi_collect.py`가 저장한 `adi-results.html`과 그 `run.json`에서 가져온다 (SUU-56이 `dashboard_letters_run.py`에서 쓴 것과 같은 패턴).
- `chunk_size`는 서버 부하를 고려해 작게 시작한다 (예: 20~50). 실제 안전한 크기는 다음 실행 티켓에서 사용자가 직접 확인한다.

### 5. 흐름
Codex가 세 파일 작성 → `python -m pytest -k adi_details` 초록 → commit·push·PR (제목 = 이 파일 첫 줄 + ` (SUU-57)`) → 사용자 merge
