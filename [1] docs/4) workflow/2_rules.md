# 이름·브랜치·PR 규칙

이 파일이 **단 하나의 원본**이다. 규칙을 바꾸려면 여기만 고친다.

## 0. 누가 이 파일을 읽나

| 누가 | 언제 |
|---|---|
| Claude Code | Linear 이슈·브랜치를 만들기 전 (`CLAUDE.md`, `/ticket`, `/spec`) |
| Codex CLI | commit·PR을 만들기 전 (`AGENTS.md`) |
| CI (`ci.yml`) | PR이 열릴 때 브랜치 이름·PR 제목을 검사. 틀리면 ❌ → merge 불가 |

## 1. Linear 이슈 제목

```
종류(영역): 결과가 보이는 한 문장
```

| 칸 | 값 | 뜻 |
|---|---|---|
| **종류** | `feat` `fix` `test` `chore` `docs` | 새 기능 / 고침 / 테스트만 / 설정·정리 / 문서 |
| **영역** | `db` `rag` `backend` `frontend` `ci` | 폴더 구조와 같음 |
| **문장** | 한국어, 40자 이내, 마침표 없음 | "무엇이 되는지"가 보여야 함 |

| 좋음 ✅ | 나쁨 ❌ | 왜 |
|---|---|---|
| `feat(db): eCFR Part 63 원문을 Supabase에 적재` | `eCFR 작업` | 뭐가 되는지 안 보임 |
| `feat(rag): 공장 설명 입력 시 관련 조항 상위 5개 반환` | `feat(rag): RAG 만들기` | 너무 큼 |
| `fix(ci): Windows에서 테스트 경로 오류 수정` | `버그 고침` | 종류·영역 없음 |

## 2. 티켓 크기

- 티켓 하나 = **테스트 하나로 "됐다 / 안 됐다" 확인 가능한 크기**
- 2~3일 넘게 걸릴 것 같으면 쪼갠다
- 티켓 하나 = 브랜치 하나 = PR 하나. 섞지 않는다

## 3. 브랜치

```
종류/suu-번호-영어짧게
```

- 예: `feat/suu-20-ecfr-ingest`, `fix/suu-21-path-error`
- 항상 `main`에서 만든다
- 소문자, 단어 사이는 `-`
- `suu-번호`가 꼭 들어가야 Linear 상태가 자동으로 바뀐다
- `main`에 직접 push 금지. 항상 PR로만
- **Codex가 일하는 동안 Claude는 git 명령을 쓰지 않는다.** 같은 폴더를 두 도구가 동시에 만지면 꼬인다. Codex가 PR 링크를 보여준 뒤에 이어서 한다
- **새 터미널을 열어 작업할 때는 예외 없이 worktree를 나눈다.** 이유가 무엇이든(같은 영역이어도) 같은 폴더에서 터미널 두 개로 git을 만지지 않는다. 한 폴더 = 한 터미널 = 한 브랜치
  - 새 터미널은 `claude --worktree <이름>`으로 연다 → `.claude/worktrees/<이름>/`에 자기 브랜치를 가진 폴더가 생기고, `.env`는 SessionStart hook(`.claude/hooks/copy_env.py`)이 복사한다
  - 루트 폴더에서 이미 터미널이 하나 돌고 있으면, 두 번째부터는 무조건 worktree다. Claude는 시작할 때 `git worktree list`로 확인하고, 루트 폴더가 이미 다른 브랜치 작업 중이면 사용자에게 worktree로 다시 열라고 말한다
  - 끝나면(PR merge 후) `git worktree remove .claude/worktrees/<이름>`으로 지운다

## 4. PR 제목

```
Linear 제목 + ` (SUU-번호)`
```

- 예: `feat(db): eCFR Part 63 원문을 Supabase에 적재 (SUU-20)`
- 제목은 설계 파일 `[5] tickets/<영역>/<종류>/SUU-번호.md` 첫 줄(`# SUU-번호 제목`)의 제목과 **글자까지 같아야** 한다. CI가 비교한다
- **모든 PR에 설계 파일이 있어야 한다.** chore/docs처럼 작은 것도 5줄짜리 설계 파일을 만든다
- PR 본문은 `.github/pull_request_template.md` 틀을 따른다

## 5. 커밋 제목

- Squash merge 하므로 **main에 남는 커밋 제목 = PR 제목** (GitHub이 끝에 `(#PR번호)`를 자동으로 붙인다)
- 브랜치 안의 중간 커밋은 자유. 단 첫 줄은 `종류(영역): 문장` 모양을 지킨다

## 6. Merge

- **Squash** 만 사용 (merge commit / rebase 금지)
- CI 초록 ✅ 이어야 merge 가능
- Codex는 PR 생성 후 `gh pr checks <PR번호> --watch`로 CI를 확인하고 결과를 사용자에게 요약한다.
- Codex는 CI 통과 후에도 자동 merge하지 않는다. 사용자가 명시적으로 merge를 승인한 경우에만 `gh pr merge <PR번호> --squash --delete-branch`를 실행한다.
- merge 후에는 로컬·원격 작업 브랜치를 삭제한다.
- 긴급 수정도 같은 길 (`fix/` 브랜치 → PR → CI → merge). 예외 없음

## 7. 한눈에

| 곳 | 모양 | 예시 |
|---|---|---|
| Linear 제목 | `종류(영역): 문장` | `feat(db): eCFR Part 63 원문을 Supabase에 적재` |
| 브랜치 | `종류/suu-번호-영어짧게` | `feat/suu-20-ecfr-ingest` |
| PR 제목 | Linear 제목 + ` (SUU-번호)` | `feat(db): eCFR Part 63 원문을 Supabase에 적재 (SUU-20)` |
| main 커밋 | PR 제목과 동일 | 위와 같음 |
| 설계 파일 | `[5] tickets/<영역>/<종류>/SUU-번호.md` | `[5] tickets/1)DB/1_feat/SUU-20.md` (12절) |
| Supabase 테이블 | `<데이터셋>_<내용>` | `ecfr_node`, `common_ingest_run` (11절) |

## 8. 테스트

- Python 3.12 + **pytest**. 설정은 루트 `pyproject.toml`
- 위치: `<영역 폴더>/tests/test_*.py` (예: `[3] backend/tests/test_calc.py`). DB는 데이터셋별로 `[2] db/tests/<데이터셋>/test_*.py`에 두고 fixture도 같은 폴더의 `fixtures/`에 둔다.
- 실행: 레포 루트에서 `python -m pytest`
- 테스트는 **Claude가 쓰고**(`/spec`), **Codex는 통과만** 시킨다. Codex는 `tests/` 아래를 수정하지 않는다
- 프론트는 **vitest**. 위치 `[4]frontend/tests/*.test.tsx`, 실행 `[4]frontend`에서 `npm test`. Codex는 여기도 수정하지 않는다
- CI가 매 PR마다 실행한다. 빨강이면 merge 불가

## 9. 파이프라인·테스트 파일 이름

- 일반 코드와 테스트 파일은 티켓 번호보다 **기능과 책임**을 이름에 쓴다. 코드는 티켓보다 오래 유지되며 여러 티켓에서 함께 수정될 수 있기 때문이다.
- 파이프라인은 `<데이터셋>_<동작>.py`로 짓는다. 예: `[2] db/pipeline/1_eCFR/ecfr_titles.py`, `echo_refresh.py`.
- 테스트는 `test_<대상 기능>.py`로 짓는다. 예: `[2] db/tests/1_ecfr/test_ecfr_titles.py`, `test_echo_refresh.py`.
- 티켓 번호는 설계 문서·커밋·PR에 기록한다. 예: `[5] tickets/1)DB/1_feat/SUU-31.md`, `feat(db): ... (SUU-31)`.
- 티켓 하나에만 존재하는 일회성 산출물이나 마이그레이션은 예외적으로 `SUU-31_<설명>.sql`처럼 티켓 번호를 앞에 붙일 수 있다.
- 한 파일이 두 개 이상의 티켓과 관련되는 것은 허용한다. 파일명을 매번 바꾸지 말고, 주 티켓은 커밋·PR 제목에, 추가 티켓은 PR 본문에 적는다.
- 한 파일의 책임이 서로 달라지면 티켓 번호를 붙이는 대신 기능별 파일로 나눈다.

## 10. CI가 검사하는 패턴

```
브랜치:  ^(feat|fix|test|chore|docs)/suu-[0-9]+-[a-z0-9-]+$
PR 제목: ^(feat|fix|test|chore|docs)\((db|rag|backend|frontend|ci)\): .{1,40} \(SUU-[0-9]+\)$
```

- 브랜치의 `suu-번호`와 PR 제목의 `(SUU-번호)`가 같아야 한다
- `[5] tickets/<영역>/<종류>/SUU-번호.md`가 있어야 하고, PR 제목 = 그 첫 줄에서 `# SUU-번호 ` 뒤의 제목 + ` (SUU-번호)`

## 11. Supabase 테이블 이름

```
<데이터셋>_<내용>
```

- 이름만 보고 **어느 자료의 표인지** 바로 알 수 있어야 한다. 접두사는 아래 6개만 쓴다.

| 접두사 | 자료 | 예시 |
|---|---|---|
| `ecfr_` | eCFR 규정 원문 | `ecfr_node`, `ecfr_block` |
| `fr_` | Federal Register 규정 변경 문서 | `fr_document`, `fr_date_event` |
| `echo_` | ECHO 시설·점검·위반·처분 | `echo_facility`, `echo_violation` |
| `adi_` | ADI + CAA Dashboard 적용 판정 회신 (Dashboard 회신도 여기) | `adi_document`, `adi_cfr_reference` |
| `rag_` | 검색 색인·평가 (청크, 임베딩, 평가셋) | `rag_chunk`, `rag_eval_case` |
| `common_` | 모든 데이터셋이 같이 쓰는 운영 표 (실행 기록, 원본 보관, release, 변경 기록) | `common_ingest_run`, `common_dataset_release` |

- 소문자와 `_`만. 접두사 없는 테이블, 목록에 없는 접두사는 만들지 않는다
- 새 데이터셋이 생기면 **이 표에 먼저 추가**하고 테이블을 만든다
- 컬럼 이름에는 접두사를 붙이지 않는다. `ecfr_node.node_key` ✅ / `ecfr_node.ecfr_node_key` ❌
- 각 테이블의 정의는 `[1] docs/2) db/` 아래 데이터셋별 구축 계획 문서 3-5절에 있다

## 12. 설계 파일 위치

```
[5] tickets/<영역>/<종류>/SUU-번호.md
```

| 제목의 칸 | 값 → 폴더 |
|---|---|
| 영역 | `db`→`1)DB` · `rag`→`2)RAG` · `backend`→`3)Backend` · `frontend`→`4)Frontend` · `ci`→`5)CI` |
| 종류 | `feat`→`1_feat` · `fix`→`2_fix` · `chore`→`3_chore` · `docs`→`4_docs` · `test`→`5_test` |

- 예: `feat(db): eCFR Part 63 원문을 Supabase에 적재` → `[5] tickets/1)DB/1_feat/SUU-20.md`
- 폴더가 없으면 만든다. `[5] tickets` 바로 아래에는 파일을 두지 않는다
- CI는 `[5] tickets` 아래 전체에서 `SUU-번호.md`를 찾는다. 같은 번호 파일을 두 곳에 두지 않는다
