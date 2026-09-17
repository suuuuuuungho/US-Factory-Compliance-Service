# SUU-98 feat(db): ECHO ZIP 2개를 실제로 처음 수집한다

## 목표
진짜 EPA 서버에서 ICIS-Air ZIP과 CAA Pipeline ZIP을 받아 `raw/{확인일}/{sha256}/`에 보관하고, 결과를 계획 문서 1-5에 적는다.

## 선행 조건 (전부 머지됨)
- SUU-94 `echo_fetch.fetch_to_file` / SUU-95 `echo_zip.inspect_zip` / SUU-96 `echo_raw.store_raw` / SUU-97 `echo_collect.main`

## 건드릴 파일
- 새 코드 없음. `echo_collect.py`를 그대로 실행한다.
- 고칠 것: `[1] docs/2) db/db 구축 계획/3_ECHO 구축 계획.md` 10항(1-5 수집 결과) — "미실행"을 실제 결과표로 바꾼다.
- 이 파일 하단 "실행 결과".

## 안 하는 것
- 코드·테스트 수정 (문제 있으면 fix 티켓으로)
- 파싱, DB 적재 (SUU-102~)
- FRS·FE&C 보조 자료
- raw ZIP을 저장소에 커밋 (`.gitignore`의 `/[2] db/*/raw/`가 막는다)

## 완료 기준 ↔ 확인 방법
| 완료 기준 | 확인 방법 |
|---|---|
| `[2] db/3) ECHO/raw/{확인일}/` 아래 ZIP 2개(각자 sha256 폴더) + `manifest.json` | 명령 종료 코드 0, 폴더 목록, `manifest.json` 항목 2개 |
| 파일별 행 수가 전수조사 수치와 대조돼 문서에 있다 | `manifest.json`의 `members[].row_count` ↔ 전수조사(시설 280,071 · 프로그램 458,110 · Subpart 191,226 · 오염물질 977,624 · 점검 1,819,117 · 배출시험 655,094 · 인증 2,583,180 · 공식처분 106,520 · 비공식처분 339,879 · 위반 102,676 · Pipeline 67,123). 다르면 "달라진 값"으로 기록 (오류 아님 — ZIP이 매주 갱신됨) |

## 실행 메모
- 명령 (본 저장소 폴더에 보관한다. worktree는 나중에 지워질 수 있다):
  ```
  python "[2] db/pipeline/3_ECHO/echo_collect.py" --root "C:\Users\Admin\Desktop\US Factory Compliance Service\[2] db\3) ECHO"
  ```
- ICIS-Air ZIP은 수백 MB(풀면 838MB). 받기 + CRC + 750만 행 세기라 몇 분 걸린다. Pipeline은 금방.
- 실패하면 `raw/`에 아무것도 안 남고 `work/*.zip`도 지워진다. `reason`에 어느 ZIP·왜가 나온다. HTML 응답이면 `ValueError("... HTML, not ZIP")` → URL이 바뀌었는지 [다운로드 목록](https://echo.epa.gov/tools/data-downloads) 확인.
- 문서 1-5에 적을 것: 확인일, ZIP별 sha256 · byte_size · `Last-Modified` · `ETag`(manifest에 있음), 파일별 행 수·열 수(`len(header)`), 전수조사 대비 차이, 소요 시간.
- 같은 날 다시 돌리면 sha256이 같을 때 `store_raw`가 항목을 재사용한다(중복 안 생김).

## 실행 순서 (Claude)
1. 위 명령 실행 → 종료 코드 0 확인
2. `manifest.json` 읽어 결과표 작성 → 계획 문서 10항 갱신 + 이 파일 "실행 결과"
3. commit → push → PR (제목 = 이 파일 첫 줄 + ` (SUU-98)`) → 사용자 merge → Linear Done

## 실행 결과
(실행 뒤 채운다)
