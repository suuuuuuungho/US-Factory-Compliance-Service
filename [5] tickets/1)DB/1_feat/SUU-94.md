# SUU-94 feat(db): ECHO ZIP을 디스크로 흘려 받으며 해시 계산

## 목표
큰 ZIP을 조각 단위로 받아 `.part` 파일에 바로 쓰고, 끝나면 이름을 바꾸고 sha256·응답 정보를 돌려준다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/3_ECHO/echo_fetch.py`
- 이미 고침 (건드리지 말 것): `pyproject.toml` — pythonpath에 `[2] db/pipeline/3_ECHO` 추가됨
- 이미 있음 (수정 금지): `[2] db/tests/3_ECHO/test_echo_fetch.py`

## 안 하는 것
- ZIP 내용 검사 (SUU-95), raw 폴더 보관 (SUU-96), 실행 진입점 (SUU-97)
- 재시도·이어받기, 진행률 출력
- `ecfr_fetch.py` import 하지 않는다. 독립 모듈
- `tests/` 아래 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| `chunk_size`씩 `read(n)`으로 읽어 `dest + ".part"`에 쓰고 `os.replace`로 이름을 바꾼다. 끝나면 `.part`가 없고 sha256이 파일과 같다 | `test_streams_chunks_to_part_file_then_renames` |
| source_url, final_url, http_status, media_type, etag, last_modified, byte_size를 돌려준다 | `test_returns_response_metadata` |
| ETag·Last-Modified 헤더가 없으면 None | `test_missing_etag_and_last_modified_are_none` |
| 응답이 HTML이면 `ValueError`를 내고 `dest`도 `.part`도 남기지 않는다 | `test_rejects_html_and_leaves_no_part_file` |

## Codex 메모

테스트가 부르는 것:

```python
from urllib.request import Request, urlopen   # 테스트가 echo_fetch.urlopen 을 monkeypatch 한다 → 모듈 최상단에서 이 이름으로 import

@dataclass(frozen=True)
class Fetched:
    path: Path
    sha256: str
    source_url: str
    final_url: str
    http_status: int
    media_type: str
    etag: str | None
    last_modified: str | None
    byte_size: int

def fetch_to_file(url: str, dest: Path, *, chunk_size: int = 1 << 20) -> Fetched
```

- 흐름: `Request(url, headers={"Accept": "application/zip"}, method="GET")` → `with urlopen(request) as response:` → `response.read(chunk_size)`를 빈 바이트가 나올 때까지 반복. 각 조각을 `hashlib.sha256`에 update 하고 `.part` 파일에 append 한다. 테스트는 **모든 `read` 호출 인자가 정확히 `chunk_size`**인지 본다 (마지막 호출까지). `read()` 인자 없이 부르면 실패.
- 임시 파일 이름은 정확히 `str(dest) + ".part"`. 끝나면 `os.replace(str(part), str(dest))`. 테스트가 `os.replace`를 가로채니 `Path.replace`가 아닌 `os.replace`를 쓴다. `dest.parent.mkdir(parents=True, exist_ok=True)` 해두면 안전.
- 응답 메타: `response.geturl()`, `response.status`, `response.headers.get("Content-Type", "")`, `response.headers.get("ETag")`, `response.headers.get("Last-Modified")` (없으면 None). `byte_size`는 실제로 쓴 바이트 합.
- HTML 거르기: **첫 조각**의 `lstrip().lower()`가 `b"<!doctype html"` 또는 `b"<html"`로 시작하면 `ValueError("ECHO response is HTML, not ZIP")`. 이때 `.part`를 닫고 지운 뒤 예외를 낸다 (`try/except` + `part.unlink(missing_ok=True)`). Content-Type만 믿지 말고 바이트로 판단한다 (eCFR `ensure_xml`과 같은 방식).
- gzip 풀기는 하지 않는다 (ZIP 자체가 압축이고 `Accept-Encoding`을 보내지 않는다).
- 표준 라이브러리만. 60줄 안팎.
- 나중에 SUU-97이 `fetch_to_file(ICIS_AIR_URL, work_dir / "ICIS-AIR_downloads.zip")`처럼 부른다.
