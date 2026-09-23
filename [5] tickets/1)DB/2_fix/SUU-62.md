# SUU-62 fix(db): Windows 긴 경로에서 원본 저장 실패 수정

## 목표
파일 경로가 260자를 넘으면 Windows에서 `ecfr_raw.save_raw`가 실패하던 버그를 고친다.

## 건드릴 파일
- 고칠 것: `[2] db/pipeline/1_eCFR/ecfr_raw.py` — `_long_path()` 헬퍼 추가, `_atomic_write`와 `save_raw`의 `mkdir`에 적용

## 안 하는 것
- 저장 경로 구조 변경 (해시 폴더 2단 그대로)
- Windows가 아닌 OS 동작 변경
- `tests/` 아래 수정

## 완료 기준 ↔ 결과
| 완료 기준 | 결과 |
|---|---|
| `test_dashboard_letters_run.py`의 실패하던 두 테스트가 통과한다 | 통과 확인 |
| 전체 `python -m pytest`가 통과한다 | 133 passed, 10 skipped |

## 원인과 고친 방법
- Windows의 기본 `MAX_PATH`는 260자다. `save_raw`가 만드는 경로(`raw/<날짜>/<sha256 64자>/<파일명>`)가 pytest의 긴 임시 폴더 경로와 합쳐지면 260자를 넘어 `.part` 파일 쓰기에서 `FileNotFoundError`가 났다.
- `_long_path(path)`: Windows에서 경로 문자열이 240자를 넘을 때만 `\\?\<절대경로>` 확장 접두사를 붙인다. 240자 이하면 원래 경로를 그대로 돌려준다.
- 240자 이하에서 그대로 두는 이유: 기존 테스트 `test_writes_part_file_first_then_renames`가 `os.replace` 호출 인자(`str(final)+".part"`, `str(final)`)를 원래 경로 문자열 그대로 비교한다. 짧은 경로에서는 접두사를 붙이지 않아야 이 비교가 그대로 통과한다.
- 적용 위치: `_atomic_write` 안에서 실제 쓰기 직전 경로만 바꾸고, `os.replace`에 넘기는 문자열도 그 바뀐 경로에서 만들어지므로 소스·대상이 항상 짝이 맞는다. `save_raw`의 `final_path.parent.mkdir(...)`도 같은 헬퍼를 통과시켜 폴더 생성 단계에서도 같은 문제가 나지 않게 했다.
