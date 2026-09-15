# SUU-45 chore(ci): PR 제목이 설계 파일 첫 줄과 다르면 CI 실패

## 목표
CI가 PR 제목을 설계 파일 첫 줄과 글자 하나하나 비교해서, 다르거나 설계 파일이 없으면 빨간불을 켠다.

## 건드릴 파일
- 고칠 것: `.github/workflows/ci.yml` `이름 규칙 검사` job — `actions/checkout` 추가, 검사 3개 추가
- 고칠 것: `[1] docs/4) workflow/2_rules.md` 4번·10번에 규칙 추가
- 만들 것: 이 파일

## 안 하는 것
- Linear API 호출, 기존 regex 검사 변경, `slack.yml`, `AGENTS.md`

## 완료 기준 ↔ 테스트
CI 설정이라 pytest 대신 진짜 PR로 확인한다.

| 완료 기준 | 확인 방법 |
|---|---|
| 이 티켓의 PR이 초록 (제목 = 설계 파일 첫 줄) | 이 PR의 `이름 규칙 검사` ✅ |
| PR 제목을 한 글자만 바꾸면 ❌, 에러에 기대 제목이 보임 | `gh pr edit --title`로 바꿔서 ❌ 확인 후 되돌림 |
| 설계 파일 없는 브랜치로 PR 열면 ❌ | 같은 스크립트를 로컬에서 `BRANCH=chore/suu-999-x`로 실행해 "설계 파일 없음" 확인 |

## 메모
- 검사 순서: 브랜치 번호 = 제목 번호 → `[5] tickets/SUU-N.md` 존재 → 첫 줄이 `# SUU-N 제목` → `제목 (SUU-N)` == PR 제목
- 첫 줄은 `utf-8-sig`로 읽어 BOM이 있어도 통과. CRLF는 `splitlines()`가 처리
- Claude가 직접 구현 (Codex 없이)
