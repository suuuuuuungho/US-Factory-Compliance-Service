---
description: Linear 티켓을 설계하고 실패하는 테스트와 브랜치를 만든다 (TDD 빨강)
argument-hint: SUU-번호
---

티켓: $ARGUMENTS

## 먼저 읽기

- `[1] docs/4) workflow/2_rules.md` — 브랜치(3번), 커밋(5번), 테스트(8번) 규칙
- Linear MCP `get_issue`로 $ARGUMENTS 읽기

## 순서

1. Linear 상태를 **In Progress**로 바꾼다 (`save_issue`).
2. 티켓을 읽고 정리한다: 건드릴 파일, 안 건드릴 것, 완료 기준. **애매하면 질문하고 멈춘다.**
3. `git checkout main && git pull` 후 브랜치를 만든다: `종류/suu-번호-영어짧게`
4. **실패하는 테스트**를 쓴다.
   - 위치: `<영역 폴더>/tests/test_<이름>.py` (예: `[3] backend/tests/test_calc.py`)
   - 완료 기준 하나당 테스트 함수 하나
   - **구현 코드는 쓰지 않는다.** 테스트가 부를 함수·모듈 이름만 정한다
5. `python -m pytest` 로 빨강을 확인한다.
6. 설계 파일 `[5] tickets/SUU-번호.md` 를 아래 형식으로 쓴다.
7. commit → push. 커밋 제목: `Linear 제목 (SUU-번호)`
8. Linear에 댓글(`save_comment`): 브랜치 이름, 설계 파일 경로, 테스트 파일 경로, 완료 기준 요약.
9. 터미널에 안내한다: `Codex 터미널에서 "SUU-번호 구현해줘"`

## 설계 파일 형식

```
# SUU-번호 제목

## 목표
한 줄.

## 건드릴 파일
- 만들 것 / 고칠 것

## 안 하는 것
- 범위 밖. Codex가 손대면 안 되는 것

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|

## Codex 메모
구현할 때 알아야 할 것: 기존 코드 위치, 데이터 형식, 주의점
```
