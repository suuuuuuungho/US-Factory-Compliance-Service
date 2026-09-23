# SUU-93 chore(ci): 작업 흐름마다 worktree를 따로 쓴다

## 목표
새 터미널을 `claude --worktree <이름>`으로 열면 자기 브랜치를 가진 폴더가 생기고 `.env`가 자동으로 복사된다.

## 건드릴 파일
- 만들 것: `.claude/settings.json`(SessionStart hook), `.claude/hooks/copy_env.py`
- 고칠 것: `.gitignore`(`.claude/worktrees/`), `[1] docs/4) workflow/2_rules.md` 3번

## 안 하는 것
- 코드·테스트 변경, Codex 설정

## 완료 기준 ↔ 확인
| 완료 기준 | 확인 |
|---|---|
| worktree에서 hook 실행 시 `.env` 생성, 원본 폴더에서는 no-op | 임시 worktree에서 `python ../../hooks/copy_env.py` → `.env` 생김 (2026-09-17 확인) |
