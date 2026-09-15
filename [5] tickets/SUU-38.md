# SUU-38 feat(db): 수집 전후 기준일이 같을 때만 원본 저장 완료

## 목표
제목 API(전) → 목차 → Part 63 XML → 저장 → 제목 API(후) 순서로 한 번에 돌리고, 전후가 같을 때만 `succeeded`로 기록한다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/1_eCFR/ecfr_collect.py`
- 이미 있음 (수정 금지): `[2] db/tests/test_ecfr_collect.py`
- 그대로 쓰기만 (수정 금지): `ecfr_titles.py`, `ecfr_structure.py`, `ecfr_fetch.py`, `ecfr_raw.py`

## 안 하는 것
- 이력 API·정정 API·이미지 다운로드 (나중 티켓)
- XML 파싱, DB
- 재시도·429 처리
- `tests/` 아래 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 전후 기준일·작업 중 여부가 같으면 `succeeded`, run.json에 기준일·항목 수·XML 해시 | `test_succeeds_when_before_and_after_match` |
| 전후가 다르면 `held`로 기록하고 예외 없이 끝난다 | `test_holds_when_as_of_changes_during_run` |
| 제목 API가 작업 중이면 받기 시작하지 않고 `held` | `test_holds_without_fetching_when_import_in_progress` |

## Codex 메모

테스트가 부르는 함수 1개:

```python
def collect(root: Path, *, fetch_titles=ecfr_titles.fetch_titles, fetch=ecfr_fetch.fetch) -> dict
```

- 두 인자는 **테스트가 가짜를 끼우는 자리**다. 기본값은 진짜 함수. 모듈 안에서 `fetch_titles()`, `fetch(url)`를 부를 때 반드시 **인자로 받은 것**을 써야 한다 (`ecfr_fetch.fetch(...)`처럼 직접 부르면 가짜가 안 끼워져 테스트가 네트워크로 나간다).
- 순서:
  1. `before = parse_title_status(fetch_titles())` → `as_of = before.up_to_date_as_of`
  2. `before.import_in_progress`가 True면 **아무것도 받지 않고** `held`로 run.json 쓰고 끝
  3. `s = fetch(structure_url(as_of))` → `structure = json.loads(s.body)` → `counts = count_by_type(find_part(structure, "63"))`
  4. `x = fetch(part_xml_url(as_of))` → `ensure_xml(x.body)` (HTML이면 ValueError 그대로 올림 — 이건 held가 아니라 오류)
  5. `save_raw(root, as_of, "title-40-structure.json", s.body, source_url=s.source_url, final_url=s.final_url, http_status=s.http_status, media_type=s.media_type)` — XML도 같은 방식으로 `"title-40-part-63.xml"`
  6. `after = parse_title_status(fetch_titles())`. `after.up_to_date_as_of != as_of` 또는 `after.import_in_progress`면 `held`, 아니면 `succeeded`
  7. run.json 쓰고 그 dict를 돌려준다
- run.json 위치: `root / "raw" / as_of.isoformat() / "run.json"` (held여도 쓴다 — 기록이 남아야 한다). 내용(dict) 키:
  `run_id`(uuid4 문자열), `dataset`(`"ecfr"`), `as_of`(`"2026-09-10"` 문자열), `import_in_progress`, `status`(`"succeeded"` / `"held"`), `reason`(held 이유: `"import_in_progress"` / `"as_of_changed"`, 성공이면 `None`), `counts`(3번의 dict), `structure_sha256`, `xml_sha256`, `started_at`, `finished_at`(UTC ISO 문자열).
  2번에서 끝날 땐 `counts`·해시는 `None`.
  테스트는 `read_run() == run`으로 비교하니 **파일에 쓴 것과 돌려준 dict가 똑같아야** 한다 (`date`는 문자열로 바꿔서 넣을 것).
- `structure_sha256`·`xml_sha256`은 `save_raw`가 돌려주는 항목의 `"sha256"`을 그대로 쓰면 된다.
- 실행 입구:
  ```python
  if __name__ == "__main__":
      root = Path(__file__).resolve().parents[2] / "1_eCFR"   # → "[2] db/1_eCFR"
      run = collect(root)
      print(json.dumps(run, indent=2, ensure_ascii=False))
      raise SystemExit(0 if run["status"] == "succeeded" else 2)
  ```
  `python "[2] db/pipeline/1_eCFR/ecfr_collect.py"` 로 돌린다. 같은 폴더의 모듈을 import 하므로 그냥 `from ecfr_titles import ...` 하면 된다 (스크립트로 실행하면 그 폴더가 sys.path 맨 앞에 온다).
- 표준 라이브러리만 (`json`, `uuid`, `datetime`, `pathlib`). 새 패키지 없음. 80줄 안팎.
- 실제 Part 63 XML은 약 26MB다. 메모리에 한 번 올리는 건 괜찮다. 스트리밍 안 해도 된다.
