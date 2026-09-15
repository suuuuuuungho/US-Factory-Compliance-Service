# Codex 규칙

이 레포에서 Codex는 **구현**만 한다. 티켓·설계·테스트는 Claude Code가 이미 해두었다.

## 시작할 때

1. `[1] docs/4) workflow/2_rules.md` 를 읽는다.
2. 사람이 준 티켓 번호(SUU-N)로:
   - `git fetch` 후 `<종류>/suu-N-*` 브랜치로 checkout (브랜치는 이미 있다)
   - `[5] tickets/SUU-N.md` 를 읽는다 (설계)
   - 거기 적힌 테스트 파일을 읽는다
3. `python -m pytest` 로 지금 빨강인 것을 확인한다.

## 하는 일

- 테스트가 **전부 초록**이 될 때까지 구현한다.
- 설계 파일의 "건드릴 파일" 범위 안에서만 고친다.
- 설계가 틀렸거나 불가능하면 **멈추고 사람에게 말한다.** 우회하지 않는다.

## 하면 안 되는 것

- `tests/` 아래 파일 수정·삭제
- `main`에 직접 push
- 설계 범위 밖 파일 수정, 리팩터링, 포맷 정리
- 새 의존성 추가 (필요하면 사람에게 묻는다)

## 끝낼 때

1. `python -m pytest` 전부 초록 확인
2. commit — 첫 줄: `[5] tickets/SUU-N.md` 첫 줄에서 `# SUU-N ` 뒤의 제목을 **글자 그대로** 복사하고 끝에 ` (SUU-N)`을 붙인다. 제목을 새로 짓거나 바꾸지 않는다
3. push
4. PR 생성: `gh pr create --base main --title "<설계 파일 첫 줄 제목> (SUU-N)"` — 커밋 첫 줄과 같은 제목. 본문은 `.github/pull_request_template.md` 형식
5. PR을 만든 뒤 `gh pr checks <PR번호> --watch`로 CI가 모두 통과할 때까지 확인한다.
6. 테스트·CI 결과와 PR 링크를 사용자에게 요약해 보여주고 멈춘다. **merge는 사용자가 명시적으로 승인한 뒤에만 한다.**
7. 사용자가 `PR #N merge해`처럼 명시적으로 승인하면 `gh pr merge N --squash --delete-branch`를 실행한다.

## 환경

- Python 3.12, pytest. 설정은 `pyproject.toml`
- 테스트 실행: 레포 루트에서 `python -m pytest`
