# SUU-96 feat(db): 검사한 ZIP을 확인일·해시 폴더에 명세와 보관

## 목표
받아서 검사까지 끝난 ZIP을 `raw/{확인일}/{sha256}/{이름}`으로 옮기고, `manifest.json`에 출처·해시·시각·멤버 명세를 적는다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/3_ECHO/echo_raw.py`
- 이미 있음 (수정 금지): `[2] db/tests/3_ECHO/test_echo_raw.py`
- 이미 있음 (import만): `echo_fetch.Fetched`, `echo_zip.MemberSpec`

## 안 하는 것
- 다운로드 (SUU-94), ZIP 검사 (SUU-95), 실행 진입점 (SUU-97), 이전 회차와 비교 (Step 4)
- ZIP 압축 풀기
- `ecfr_raw.py` import 하지 않는다 (bytes를 통째로 받는 구조라 못 쓴다). 독립 모듈
- `tests/` 아래 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| ZIP이 `root/raw/{as_of}/{sha256}/{이름}`으로 **이동**(원래 자리엔 없음)되고, manifest 항목에 name·path·source_url·final_url·http_status·media_type·etag·last_modified·sha256·byte_size·fetched_at·members가 있다. 돌려준 항목 = 파일에 쓴 항목 | `test_moves_zip_under_hash_folder_and_records_manifest` |
| 같은 sha256을 두 번 보관하면 파일·항목이 하나만 남고, 두 번째 임시 파일은 지운다. 돌려준 항목은 처음 것 | `test_storing_same_hash_twice_keeps_one_file_and_one_entry` |
| ZIP 2개(ICIS-Air, Pipeline)가 같은 날 manifest 하나에 순서대로 들어간다 | `test_two_different_zips_share_one_manifest` |

## Codex 메모

테스트가 부르는 것:

```python
from echo_fetch import Fetched
from echo_zip import MemberSpec

def store_raw(root: Path, as_of: date, fetched: Fetched, members: Sequence[MemberSpec]) -> dict
```

- 경로: `raw_root = root / "raw" / as_of.isoformat()`, `final = raw_root / fetched.sha256 / fetched.path.name`, `manifest_path = raw_root / "manifest.json"`.
- manifest는 **JSON 리스트**. 있으면 읽고 없으면 `[]`. 항목 dict 키 순서·값:
  `name`(= `fetched.path.name`), `path`(`final.relative_to(root).as_posix()`), `source_url`, `final_url`, `http_status`, `media_type`, `etag`, `last_modified`, `sha256`, `byte_size`, `fetched_at`(`datetime.now(timezone.utc).isoformat()` — `+00:00`으로 끝남), `members`(`[dataclasses.asdict(m) for m in members]`).
- 중복: manifest에 `sha256`이 같은 항목이 이미 있으면 → `fetched.path.unlink(missing_ok=True)`로 임시 파일을 치우고 **그 항목을 그대로** 돌려준다. 파일을 다시 쓰지도, 항목을 추가하지도 않는다.
- 이동: `final.parent.mkdir(parents=True, exist_ok=True)` 후 `shutil.move(str(fetched.path), str(final))`. (`os.replace`는 드라이브가 다르면 실패하니 `shutil.move`를 쓴다. 테스트는 이동 방식을 가로채지 않는다.)
- manifest 쓰기: `json.dumps(manifest, ensure_ascii=False, indent=2)`를 `manifest_path + ".part"`에 쓰고 `os.replace`로 바꾼다 (`ecfr_raw._atomic_write`와 같은 방식). 테스트는 `read_text` 후 `json.loads`로 비교하니 돌려주는 dict와 파일 내용이 완전히 같아야 한다.
- 표준 라이브러리만 (`dataclasses`, `datetime`, `json`, `os`, `shutil`, `pathlib`). 50줄 안팎.
- 나중에 SUU-97이 이렇게 부른다:
  ```python
  fetched = fetch_to_file(url, work_dir / name)
  members = inspect_zip(fetched.path, required=ICIS_AIR_MEMBERS)
  entry = store_raw(root, date.today(), fetched, members)
  ```
