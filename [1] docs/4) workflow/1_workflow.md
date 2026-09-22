# 개발 자동화 Flow

## 1. 한 줄 요약

> 터미널에 만들고 싶은 기능을 던지면 → Claude가 티켓을 만들고 설계하고 → Codex가 구현하고 → 로봇(CI)이 검사하고 → 사람이 Merge 누르면 → 자동 배포되고 → Slack이 알려준다.

## 2. 그림으로 보기

```
[사람]   Claude Code 터미널에서
         /ticket "공장 정보 입력하면 적용 가능한 Part 63 조항 후보를 보여주는 기능"
   │
   ▼
[Claude] 애매하면 질문 1~2개 → 티켓 초안 여러 개를 보여줌
   │
   ▼
[사람]   "OK" (또는 빼기 / 합치기 / 순서 바꾸기)
   │
   ▼
[Claude] Linear에 이슈 발행 (제목 규칙은 2_rules.md)
   │
   ▼
[사람]   /spec SUU-20
   │
   ▼
[Claude] ├─ 티켓 읽고 "무엇을, 어디까지, 어떻게 확인할지" 정리
         ├─ 실패하는 테스트 코드 작성                  ← TDD "빨강"
         ├─ 설계 파일 저장: [5] tickets/SUU-20.md
         └─ 브랜치 feat/suu-20-xxx 에 push + Linear 댓글
   │                                            ─▶ Linear: In Progress (/spec이 바꿈)
   ▼
[사람]   Codex 터미널에서  "SUU-20 구현해줘"
   │
   ▼
[Codex]  ├─ 브랜치의 설계 파일 + 테스트 읽음
         ├─ 테스트가 통과할 때까지 코드 작성          ← TDD "초록"
         └─ commit → push → PR 생성
   │                                            ─▶ Linear: In Review (자동)
   ▼                                            ─▶ Slack: PR 열림 🟡
[CI]     테스트 자동 실행 + 이름 규칙 검사
   │        실패 → Slack 🔴 → Codex가 고침 → 다시 push
   ▼        성공 ✅
[사람]   PR 확인 → Merge 버튼 (Squash)
   │                                            ─▶ Linear: Done (자동)
   ▼                                            ─▶ Slack: 병합 완료 🟢
[CD]     main에 합쳐지면 자동 배포
                                                ─▶ Slack: 배포 성공 / 실패
```

## 3. 누가 무엇을 하나

| 역할 | 하는 일 | 안 하는 일 |
|---|---|---|
| **사람** | 기능 아이디어 던지기, 티켓 확인, PR 확인·Merge | 코드 직접 작성, 티켓 직접 작성 |
| **Linear** | 티켓·상태판 (Todo → In Progress → In Review → Done) | - |
| **Claude Code** | 티켓 만들기, 티켓 분석, 변경 범위 결정, 완료 기준, **실패하는 테스트 작성** | 기능 구현 |
| **Codex CLI** | 테스트 통과시키는 구현, commit / push / PR 생성·CI 확인·결과 요약 | 테스트 수정·삭제 (금지), 사용자 승인 전 merge |
| **GitHub Actions** | CI (테스트 + 규칙 검사), CD (배포), Slack 알림 | - |
| **Slack** | 알림만 받음 | - |

## 4. 단계별로 자세히

### 0단계. 티켓 만들기 — `/ticket`

| | |
|---|---|
| 누가 | 사람이 시작, Claude가 작성 |
| 입력 | 터미널에 만들고 싶은 기능 한두 줄 |
| Claude가 하는 일 | 1) 애매하면 질문 2) 테스트 하나로 확인 가능한 크기로 쪼갬 3) 초안 보여줌 4) 사람이 OK 하면 Linear에 발행 |
| 결과물 | Linear 이슈 여러 개 (제목: `종류(영역): 문장`) |
| 완료 확인 | Linear에 이슈가 보이고 제목이 규칙에 맞음 |

### 1단계. 설계 — `/spec SUU-20`

| | |
|---|---|
| 누가 | Claude Code |
| 입력 | Linear 이슈 번호 |
| Claude가 하는 일 | 1) 이슈 읽기 2) 건드릴 파일·범위 정하기 3) 완료 기준 쓰기 4) **실패하는 테스트 코드** 작성 (`<영역>/tests/test_*.py`, pytest) 5) `main`에서 브랜치 만들기 6) 설계 파일 + 테스트 commit·push 7) Linear 댓글로 요약 |
| 결과물 | 브랜치 `feat/suu-20-xxx`, 설계 파일 `[5] tickets/SUU-20.md`, 실패하는 테스트 |
| Linear | `/spec`이 상태를 In Progress로 바꿈 (Linear 자동화는 PR 열림·merge만 다룸) |
| 완료 확인 | 테스트 돌리면 빨강 (아직 구현 없으니 당연) |

### 2단계. 구현 — Codex

| | |
|---|---|
| 누가 | Codex CLI |
| 입력 | "SUU-20 구현해줘" |
| Codex가 하는 일 | 1) `AGENTS.md` 규칙 읽기 2) 브랜치 checkout 3) 설계 파일 + 테스트 읽기 4) 테스트 통과할 때까지 구현 5) commit → push → PR 생성 6) CI 확인 및 결과 요약 |
| 하면 안 되는 것 | 테스트 파일 수정·삭제, `main`에 직접 push |
| 이때 Claude는 | **git을 건드리지 않는다** (브랜치 전환·커밋 금지). 같은 폴더를 같이 쓰기 때문. Codex가 PR 링크를 보여준 뒤에 이어서 한다 |
| 결과물 | PR (제목: Linear 제목 + ` (SUU-20)`) |
| 자동으로 | Linear → In Review, Slack 🟡 |
| 완료 확인 | 로컬 테스트와 CI가 모두 초록이고, Codex가 결과를 요약한 뒤 merge 승인 대기 |

### 3단계. 검사 — CI

| | |
|---|---|
| 누가 | GitHub Actions |
| 언제 | PR 열릴 때, push 될 때마다 |
| 하는 일 | 1) 테스트 실행 2) 브랜치 이름·PR 제목 규칙 검사 |
| 실패하면 | Slack 🔴 → Codex가 고쳐서 다시 push |
| 완료 확인 | PR에 초록 체크 ✅ |

### 4단계. 확인·Merge — Codex 확인, 사람 승인

| | |
|---|---|
| 누가 | Codex + 사람 |
| 하는 일 | Codex가 PR과 CI를 확인·요약 → 사람이 명시적으로 승인 → Codex가 `gh pr merge <PR번호> --squash --delete-branch` 실행 |
| 자동으로 | Linear → Done, Slack 🟢, merge 후 로컬·원격 브랜치 삭제 |

### 5단계. 배포 — CD

| | |
|---|---|
| 누가 | Render + Vercel + Supabase |
| 언제 | `main`에 합쳐질 때 |
| 하는 일 | 백엔드 → Render(`render.yaml`), 프론트 → Vercel, DB → Supabase 마이그레이션 |
| 자동으로 | Render·Vercel Slack 알림(각 대시보드 연동) |

## 5. 만들 파일 (9개)

| 파일 | 역할 | 한 줄 설명 |
|---|---|---|
| `[1] docs/4) workflow/2_rules.md` | 규칙 | 제목·브랜치·PR·커밋 규칙. **단 하나의 원본** |
| `.claude/commands/ticket.md` | Claude | `/ticket "기능"` → 티켓 초안 → 확인 → Linear 발행 |
| `.claude/commands/spec.md` | Claude | `/spec SUU-20` → 설계 + 실패 테스트 + 브랜치 |
| `AGENTS.md` (루트) | Codex | Codex가 지킬 규칙 (설계 파일 읽기, 테스트 금지, PR 제목) |
| `.github/workflows/ci.yml` | CI | pytest 실행 + 규칙 검사 |
| `pyproject.toml` | 테스트 | pytest 설정 (`[3] backend` 같은 폴더를 import 가능하게) |
| `render.yaml` | CD | main merge 시 Render 배포 |
| `.github/workflows/slack.yml` | 알림 | PR 열림 / CI 실패 / 병합 / 배포 결과 |
| `.github/pull_request_template.md` | PR | PR 본문 틀 (이슈 번호, 테스트 결과) |

+ `CLAUDE.md`에 "규칙 파일을 읽는다" 한 줄 추가.

설계 결과물은 `[5] tickets/SUU-번호.md` 로 레포 안에 남긴다. (`[1] docs`, `[2] db` 처럼 최상위 폴더. Codex가 Linear 없이도 읽을 수 있게)

## 6. 설정만 하면 되는 것 (코드 0줄)

| 어디 | 무엇 | 왜 |
|---|---|---|
| Linear → Settings → Integrations → GitHub | 레포 연결. **GitHub Issues sync는 끄기** | 브랜치 이름에 `suu-20`이 있으면 PR을 이슈에 자동 연결 |
| Linear → Settings → Workflows & automations | PR open → In Review, PR merge → Done | 상태 자동 변경 |
| GitHub → Settings → Secrets | `SLACK_WEBHOOK_URL` | Slack 알림용 |
| GitHub → Settings → Branches → main | PR 필수, CI 통과 필수 | main 직접 push 금지 |
| GitHub → Settings → General | Squash merge만 허용, 머지 후 브랜치 자동 삭제 | 히스토리 깔끔 |
| Vercel | GitHub 레포 연결 + Root Directory `[4]frontend` + `NEXT_PUBLIC_API_URL` | main merge 시 자동 배포, PR마다 미리보기 |
| Render | GitHub 레포 연결(Blueprint) + 환경변수 4개 + Slack 연동 | main merge 시 백엔드 자동 배포 |

> "승인 1명 필수"는 켜지 않는다. GitHub은 자기 PR을 자기가 승인 못 하게 막아서 혼자 개발하면 merge가 안 된다. **Merge 버튼을 누르는 것이 승인**이다.

## 7. 구축 순서 (하나씩 만들고 확인)

| 순서 | 만드는 것 | 이렇게 확인 | 상태 |
|---|---|---|---|
| 0 | `1_workflow.md`, `2_rules.md`, `CLAUDE.md` 한 줄 | 승인 후 바로 | ✅ |
| 1 | `ci.yml` | 테스트용 PR 열면 ✅ / ❌ 표시 뜸. 이름 틀린 브랜치는 ❌ | ✅ SUU-28
| 2 | GitHub 브랜치 보호 + merge 설정 | main에 직접 push 하면 거부됨 | ✅
| 3 | Linear ↔ GitHub 연동 | PR 열면 이슈에 자동 연결, merge 시 Done |  ✅
| 4 | `slack.yml` | PR 열면 Slack에 메시지 옴 | ✅ SUU-29
| 5 | `/ticket`, `/spec`, `AGENTS.md`, PR 템플릿, pytest CI | 진짜 티켓 하나로 Claude → Codex → PR 끝까지 돌려봄 | 🟡 SUU-30 파일 완료, 실전 검증 남음
| 6 | Vercel 연결(cd.yml 없음) + slack.yml deployment_status | main merge 시 Slack에 🚀 배포 알림, `https://us-factory-compliance-service.vercel.app` | ✅ SUU-165 (SUU-140~143에서 한 번 연결했다가 SUU-144로 초기화. Root Directory 공백 불가 → `[4]frontend`) |
| 6-b | `render.yaml` + Render 연결 | `/health` 200 | SUU-160 |

## 8. 결정 기록 (왜 이렇게 했나)

| 결정 | 이유 |
|---|---|
| 테스트 코드는 Claude가 쓴다 | 진짜 TDD. Codex 목표가 "이 테스트 통과"로 명확해짐 |
| Python 3.12 + pytest | 백엔드·DB 파이프라인이 Python. 프론트는 스택 정해지면 추가 |
| 티켓은 Claude가 쓰고 사람이 확인한다 | 사람이 쓰면 크고 애매한 티켓이 나오기 쉬움. Claude가 쪼개면 테스트 크기가 됨 |
| Codex는 CLI(로컬) | Claude Code와 같은 터미널·같은 폴더. `AGENTS.md` 자동으로 읽음 |
| Linear 상태는 기본 GitHub 연동 | 코드 0줄. 이전의 직접 스크립트 방식은 버림 |
| 브랜치는 main 하나 + 짧은 브랜치 | 혼자 개발 + 자동 배포라 develop / release 불필요 |
| Squash merge만 | 티켓 하나 = main 커밋 하나 |
| 이전 `.github` 파일은 버림 | 새로 만든다. 필요하면 git 히스토리에서 꺼냄 |
| 배포는 Vercel + Supabase | 설정만으로 자동 배포. 백엔드는 스택 정해지면 추가 |
