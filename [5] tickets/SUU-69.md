# SUU-69 feat(db): eCFR 실제 적재를 실행하는 CLI 진입점

## 목표
`python ecfr_ingest.py`로 실제 Part 63 데이터를 Supabase에 등록·적재·공개할 수 있게 한다.

## 건드릴 파일
- 고칠 것: `[2] db/pipeline/1_eCFR/ecfr_ingest.py` — `_latest_as_of(raw_root) -> str` 함수와 `if __name__ == "__main__":` 블록 추가
- 만들 것: `[2] db/tests/1_eCFR/test_ecfr_ingest_cli.py` — 이미 작성됨 (빨강 확인 완료, `_latest_as_of`만 테스트)
- 고칠 것: `requirements.txt` — `supabase` 패키지 추가

## 안 하는 것
- 이 스크립트를 실제로 실행해서 진짜 데이터를 넣는 것 (병합 후 사람이 직접 실행)
- 여러 title/part 지원, 스케줄링/자동 갱신
- `__main__` 블록 자체의 자동 테스트 (실제 Supabase 연동이라 코드 리뷰로만 확인 — 완료 기준 3번)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| raw/ 아래 여러 as_of 폴더 중 가장 최근 날짜를 고른다 | `test_picks_the_most_recent_as_of_folder` |
| raw/ 폴더에 as_of가 하나도 없으면 명확한 에러를 낸다 | `test_raises_a_clear_error_when_raw_has_no_as_of_folders` |
| `python ecfr_ingest.py` 실행 시 release_id가 출력된다 | 자동 테스트 없음 — 코드 리뷰로 확인 |

## Codex 메모
- **참고 스타일**: `[2] db/pipeline/1_eCFR/ecfr_parse.py`의 `__main__` 블록과 같은 모양으로 만들면 된다.
  ```python
  if __name__ == "__main__":
      pipeline_root = Path(__file__).resolve().parents[2] / "1) eCFR"
      raw_root = pipeline_root / "raw"
      selected_as_of = (
          sys.argv[1] if len(sys.argv) > 1 else _latest_as_of(raw_root)
      )
      ...
  ```
- **`_latest_as_of` 에러 메시지**: `raw_root`에 폴더가 하나도 없으면 `max()`가 그냥 `ValueError: max() arg is an empty sequence`를 던진다. 이건 사람이 읽기 불편하니 `FileNotFoundError(f"no as_of folders found under {raw_root}")`처럼 raw_root 경로를 포함한 메시지로 직접 raise한다.
- **client 생성**: `.env`에 이미 `SUPABASE_URL`, `SUPABASE_SECRET_KEY`(service_role, RLS 우회)가 있다. `python-dotenv` 없이도 되면 `os.environ`으로 바로 읽어도 되고, 이미 다른 곳에서 `.env` 로딩 방식을 쓰고 있으면 그거에 맞춘다(레포에 기존 패턴이 없으면 `os.environ.get`으로 충분).
- **supabase 패키지**: `from supabase import create_client`. 정확한 버전 핀은 최신 안정 버전으로 넣으면 된다.
- **root 인자**: `run_ecfr_ingest(root, as_of, client=client)`의 `root`는 `pipeline_root`(= `raw/`, `parsed/`의 부모 폴더)다. `raw_root`가 아니다.
