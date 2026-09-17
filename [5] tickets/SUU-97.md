# SUU-97 feat(db): ECHO 수집을 한 번에 실행하는 CLI 진입점

## 목표
명령 하나로 ZIP 2개를 받고 → 검사하고 → 둘 다 통과했을 때만 보관하고 → ZIP마다 요약을 돌려준다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/3_ECHO/echo_collect.py`
- 이미 있음 (수정 금지): `[2] db/tests/3_ECHO/test_echo_collect.py`
- 이미 있음 (import만): `echo_fetch.fetch_to_file`, `echo_zip.inspect_zip / ICIS_AIR_MEMBERS / PIPELINE_MEMBERS / ZipCheckError`, `echo_raw.store_raw`

## 안 하는 것
- 스케줄·자동 갱신 (Step 4), 이전 회차와 비교, FRS·FE&C 보조 자료
- 실제 네트워크 실행 (SUU-98)
- 재시도, 진행률 출력
- `ecfr_collect.py` import 하지 않는다 (다른 구조). 모양만 참고
- `tests/` 아래 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| ICIS-Air → Pipeline 순서로 받고, 각각 `ICIS_AIR_MEMBERS` / `PIPELINE_MEMBERS`로 검사하고, 둘 다 통과하면 순서대로 보관한다. 돌려준 `zips`에 ZIP마다 name·sha256·byte_size·member_count·row_count(CSV 행 합, None 제외) | `test_summarizes_each_zip_with_hash_member_and_row_counts` |
| 하나라도 검사 실패면 `status="failed"`, `reason`에 ZIP 이름과 오류 문구. `store_raw`는 한 번도 안 부르고 `raw/`도 없고 `work/`의 ZIP도 치운다 | `test_check_failure_stores_nothing` |
| `main(argv) -> int`: succeeded면 0, 아니면 2 | `test_main_exit_code_follows_status` |

## Codex 메모

테스트가 부르는 것:

```python
ICIS_AIR_URL = "https://echo.epa.gov/files/echodownloads/ICIS-AIR_downloads.zip"
PIPELINE_URL = "https://echo.epa.gov/files/echodownloads/pipeline_caa_downloads.zip"

def collect(
    root: Path,
    *,
    as_of: date | None = None,          # None 이면 date.today()
    fetch_to_file=fetch_to_file,        # (url, dest) -> Fetched
    inspect_zip=inspect_zip,            # (path, *, required) -> list[MemberSpec]
    store_raw=store_raw,                # (root, as_of, fetched, members) -> dict
) -> dict

def main(argv: list[str] | None = None) -> int
```

- 대상 2개는 상수 튜플로: `(ICIS_AIR_URL, "ICIS-AIR_downloads.zip", ICIS_AIR_MEMBERS)`, `(PIPELINE_URL, "pipeline_caa_downloads.zip", PIPELINE_MEMBERS)`. 이 순서 그대로.
- 흐름 (**받기·검사를 둘 다 끝낸 뒤에 보관**한다. 첫 ZIP이 통과해도 두 번째가 실패하면 아무것도 보관하지 않는다):
  1. `work = root / "work"`. ZIP마다 `fetched = fetch_to_file(url, work / name)` → `members = inspect_zip(fetched.path, required=required)` → 리스트에 모아둔다.
  2. 전부 통과 → ZIP마다 `store_raw(root, as_of, fetched, members)`.
  3. 실패(`ZipCheckError`, `ValueError`, `OSError`/`URLError`) → `status="failed"`, `reason=f"{name}: {exc}"`, `work/*.zip` 전부 `unlink(missing_ok=True)`, 곧바로 돌려준다. `raw/` 아래에 아무것도 만들지 않는다 (run.json도 안 쓴다).
- 돌려주는 dict 키: `status`("succeeded"/"failed"), `as_of`(`isoformat()`), `reason`(성공이면 None), `zips`(리스트), `started_at`, `finished_at`(둘 다 `datetime.now(timezone.utc).isoformat()`). 테스트는 앞 4개만 본다.
- `zips` 항목: `{"name", "sha256", "byte_size", "member_count": len(members), "row_count": sum(m.row_count for m in members if m.row_count is not None)}`. 이 5개 키만 (딕셔너리 `==` 비교라 키가 더 있으면 실패).
- `main(argv)`: `argparse`로 `--root`(기본 `Path(__file__).resolve().parents[2] / "3) ECHO"`, 이 폴더는 이미 있다). `run = collect(Path(args.root))` → `print(json.dumps(run, indent=2, ensure_ascii=False))` → `return 0 if run["status"] == "succeeded" else 2`. 테스트가 `echo_collect.collect`를 monkeypatch 하니 `main` 안에서 **모듈 전역 이름 `collect`로** 부른다 (기본 인자로 묶어두면 안 된다). `if __name__ == "__main__": raise SystemExit(main())`.
- 성공 시 `work/` ZIP은 `store_raw`가 이미 옮겼으니 따로 지울 게 없다.
- 표준 라이브러리만. 80줄 안팎.
- SUU-98이 `python "[2] db/pipeline/3_ECHO/echo_collect.py"`로 실제 실행한다. ICIS-Air ZIP은 수백 MB — 받기·검사에 몇 분 걸리는 게 정상.
