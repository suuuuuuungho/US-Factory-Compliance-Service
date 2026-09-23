# SUU-37 feat(db): 받은 원본을 기준일 폴더에 해시와 함께 저장

## 목표
받은 바이트를 `raw/{기준일}/{sha256}/{파일명}`에 그대로 저장하고, `manifest.json`에 출처·상태·해시·시각을 기록한다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/1_eCFR/ecfr_raw.py`
- 이미 고침 (건드리지 말 것): `.gitignore` — `[2] db/*/raw/`, `[2] db/*/parsed/` 무시
- 이미 있음 (수정 금지): `[2] db/tests/1_ecfr/test_ecfr_raw.py`

## 안 하는 것
- 네트워크 (SUU-36), 전후 비교·실행 (SUU-38), 파싱
- `ecfr_fetch.py`를 import 하지 않는다 (아직 main에 없다). 인자는 전부 기본 타입으로 받는다
- 기존 파일 삭제·정리
- `tests/` 아래 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 파일의 sha256이 manifest 항목과 같고, 항목에 source_url·final_url·http_status·media_type·byte_size·fetched_at이 있다 | `test_saves_file_under_hash_folder_and_records_manifest` |
| 같은 내용을 두 번 저장하면 파일·manifest 항목이 하나만 남는다 | `test_saving_same_content_twice_keeps_one_file_and_one_entry` |
| `.part`에 먼저 쓰고 다 쓴 뒤 이름을 바꾼다. 끝나면 `.part`가 없다 | `test_writes_part_file_first_then_renames` |

## Codex 메모

테스트가 부르는 함수 1개:

```python
def save_raw(
    root: Path, as_of: date, name: str, body: bytes, *,
    source_url: str, final_url: str, http_status: int, media_type: str,
) -> dict
```

- 저장 경로: `root / "raw" / as_of.isoformat() / sha256(body).hexdigest() / name`. 폴더는 `mkdir(parents=True, exist_ok=True)`.
- manifest: `root / "raw" / as_of.isoformat() / "manifest.json"`. **JSON 리스트**. 항목(dict) 키:
  `name`, `path`(root 기준 상대경로, `/` 구분 — `as_posix()`), `source_url`, `final_url`, `http_status`, `media_type`, `byte_size`(= `len(body)`), `sha256`, `fetched_at`(UTC ISO 문자열, `datetime.now(timezone.utc).isoformat()`).
  돌려주는 값 = 방금 넣은(또는 이미 있던) 항목 dict. 테스트는 `read_manifest() == [entry]`로 비교하니 **파일에 쓴 것과 돌려준 것이 똑같아야** 한다.
- 중복: manifest에 `name`과 `sha256`이 같은 항목이 이미 있으면 파일을 다시 쓰지 않고 그 항목을 그대로 돌려준다. 새 항목을 추가하지 않는다.
- **원자적 쓰기**: 데이터 파일은 `최종경로 + ".part"`(예: `x.xml.part`)에 먼저 쓰고 `os.replace(part, final)`로 바꾼다.
  테스트가 `os.replace`를 가로채서 `(str(final) + ".part", str(final))` 호출이 있었는지 본다. 그러니 **`os.replace`를 쓰고**(`Path.replace`도 내부에서 `os.replace`를 부르므로 됨), 임시 파일 이름은 정확히 `최종 파일명 + ".part"`. `tempfile`로 랜덤 이름을 만들면 테스트가 실패한다.
  manifest.json도 같은 방식으로 쓰면 좋다 (필수는 아님).
- 표준 라이브러리만 (`hashlib`, `json`, `os`, `pathlib`, `datetime`). 새 패키지 없음. 50줄 안팎이면 충분하다.
- 나중에 SUU-38이 이렇게 부른다: `save_raw(root, as_of, "title-40-part-63.xml", fetched.body, source_url=fetched.source_url, ...)`.
