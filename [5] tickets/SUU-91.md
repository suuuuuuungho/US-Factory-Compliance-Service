# SUU-91 chore(rag): 작업 중 남은 파일을 정리한다

## 목표
SUU-80·81 뒤 `git status`에 남은 파일을 정리해 다음 티켓을 깨끗한 상태에서 시작한다.

## 건드릴 파일
- 추가: `[6] rag/PoC/SUU-76 poc 결과.md`, `suu76_rows.json`, `suu76_search.json` (SUU-76 PoC 기록), `[7] daily_brief/2026-09-16 brief.md`
- 고침: `[7] daily_brief/2026-09-15 brief.md`, `.gitignore` (Codex 테스트 임시 폴더 `.codex-*/`, `tmp/`, `t u v w` 무시)

## 안 하는 것
- 코드·테스트 변경 없음

## 완료 기준 ↔ 확인
| 완료 기준 | 확인 |
|---|---|
| `git status` 깨끗 | 머지 후 `git status --short` 출력 없음 |
