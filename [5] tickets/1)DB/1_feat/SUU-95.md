# SUU-95 feat(db): ECHO ZIP 무결성과 필수 CSV 11개를 검사

## 목표
받은 ZIP이 깨지지 않았는지, 필수 CSV가 다 있는지 검사하고, 멤버마다 이름·바이트·헤더·행 수를 담은 명세를 돌려준다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/3_ECHO/echo_zip.py`
- 이미 있음 (수정 금지): `[2] db/tests/3_ECHO/test_echo_zip.py`

## 안 하는 것
- 값 해석·정규화·날짜 변환 (Step 2 파서), raw 폴더 보관 (SUU-96), 다운로드 (SUU-94), 실행 (SUU-97)
- ZIP 압축 풀어서 디스크에 쓰기 — 검사와 명세만 만든다
- fixture 파일 커밋 — 테스트가 `zipfile`로 직접 만든다
- `tests/` 아래 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 필수 멤버 상수: ICIS-Air 10개, Pipeline 1개 (전수조사 문서의 실제 이름) | `test_required_member_constants_match_survey` |
| 멤버마다 `name/byte_size/header/row_count` 명세. 행 수는 헤더 제외, 셀 안 줄바꿈은 행으로 안 셈. 필수 아닌 멤버도 명세에 넣고, `.csv`가 아니면 header·row_count는 None | `test_returns_spec_per_member_with_header_and_exact_row_count` |
| UTF-8 BOM은 헤더 첫 열 이름에서 뺀다 | `test_strips_utf8_bom_from_header` |
| 필수 멤버가 빠지면 `ZipCheckError`에 빠진 이름이 들어간다 | `test_missing_required_member_names_what_is_missing` |
| `..`가 들어간 멤버 경로는 `ZipCheckError`에 그 이름을 담아 거부 | `test_path_escaping_work_folder_is_rejected` |
| CRC가 안 맞으면 `ZipCheckError`에 "CRC" 문구 | `test_crc_mismatch_is_rejected` |
| ZIP이 아니면 `ZipCheckError`에 "ZIP" 문구 | `test_not_a_zip_is_rejected` |
| `ZipFile.read()`(멤버 통째로) 쓰지 않고 `open()`으로 흘려 읽는다 | `test_does_not_read_whole_member_into_memory` |

## Codex 메모

테스트가 부르는 것:

```python
ICIS_AIR_MEMBERS: tuple[str, ...]   # 10개
PIPELINE_MEMBERS: tuple[str, ...]   # ("PIPELINE_CAA_00_COMPLETE.csv",)

class ZipCheckError(ValueError): ...

@dataclass(frozen=True)
class MemberSpec:
    name: str
    byte_size: int          # ZipInfo.file_size (압축 풀린 크기)
    header: list[str] | None
    row_count: int | None

def inspect_zip(path: Path, *, required: Sequence[str]) -> list[MemberSpec]
```

- ICIS-Air 10개 이름 (`[1] docs/2) db/db overview/2_db 전수조사 결과.md` 143~152줄):
  `ICIS-AIR_FACILITIES.csv`, `ICIS-AIR_PROGRAMS.csv`, `ICIS-AIR_PROGRAM_SUBPARTS.csv`, `ICIS-AIR_POLLUTANTS.csv`, `ICIS-AIR_FCES_PCES.csv`, `ICIS-AIR_STACK_TESTS.csv`, `ICIS-AIR_TITLEV_CERTS.csv`, `ICIS-AIR_FORMAL_ACTIONS.csv`, `ICIS-AIR_INFORMAL_ACTIONS.csv`, `ICIS-AIR_VIOLATION_HISTORY.csv`
- 검사 순서 (먼저 걸리는 것부터 예외):
  1. `zipfile.is_zipfile(path)`가 False → `ZipCheckError("not a ZIP file: ...")`. (`zipfile.BadZipFile`도 잡아서 같은 예외로 바꾼다)
  2. 멤버 이름 검사: `PurePosixPath(name).parts`에 `".."`가 있거나 `name.startswith(("/", "\\"))`이거나 `":"`가 들어가면 → `ZipCheckError(f"unsafe member path: {name}")`
  3. 필수 누락: `missing = [m for m in required if m not in names]` → `ZipCheckError(f"missing required members: {', '.join(missing)}")`
  4. CRC: `zf.testzip()`이 이름을 돌려주면 → `ZipCheckError(f"CRC mismatch in {name}")`. (`testzip`은 내부에서 `open()`으로 흘려 읽으니 메모리 안전. 이후 CSV 읽다가 `BadZipFile("Bad CRC-32 ...")`가 나도 같은 문구로 바꾼다)
- 명세 만들기: `for info in zf.infolist()` (디렉터리 항목 `info.is_dir()`은 건너뜀). 이름이 `.csv`(대소문자 무시)로 끝나면:
  ```python
  with zf.open(info) as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text:
      reader = csv.reader(text)
      header = next(reader, None) or []
      row_count = sum(1 for _ in reader)
  ```
  `newline=""`을 꼭 줘야 셀 안 `\r\n`이 행으로 안 쪼개진다. `utf-8-sig`가 BOM을 뗀다. `errors=` 인자는 주지 않는다 (기본 strict — 인코딩 깨지면 예외가 나야 한다. 계획 2-1).
  `.csv`가 아니면 `header=None, row_count=None`.
- `ZipFile.read(name)`는 어디서도 부르지 않는다. 테스트가 그 메서드를 막아 놓는다.
- 표준 라이브러리만 (`zipfile`, `csv`, `io`, `dataclasses`, `pathlib`). 70줄 안팎.
- 나중에 SUU-97이 이렇게 부른다: `inspect_zip(zip_path, required=ICIS_AIR_MEMBERS)` / `inspect_zip(zip_path, required=PIPELINE_MEMBERS)`. 실제 파일은 CSV 하나가 수백 MB이니 스트리밍이 필수다.
