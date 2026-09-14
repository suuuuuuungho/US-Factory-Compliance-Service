# 이름·브랜치·PR 규칙

이 파일이 **단 하나의 원본**이다. 규칙을 바꾸려면 여기만 고친다.

## 0. 누가 이 파일을 읽나

| 누가 | 언제 |
|---|---|
| Claude Code | Linear 이슈·브랜치를 만들기 전 (`CLAUDE.md`, `/ticket`, `/design`) |
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

## 4. PR 제목

```
Linear 제목 + ` (SUU-번호)`
```

- 예: `feat(db): eCFR Part 63 원문을 Supabase에 적재 (SUU-20)`
- PR 본문은 `.github/pull_request_template.md` 틀을 따른다

## 5. 커밋 제목

- Squash merge 하므로 **main에 남는 커밋 제목 = PR 제목**
- 브랜치 안의 중간 커밋은 자유. 단 첫 줄은 `종류(영역): 문장` 모양을 지킨다

## 6. Merge

- **Squash** 만 사용 (merge commit / rebase 금지)
- CI 초록 ✅ 이어야 merge 가능
- 사람이 Merge 버튼을 누르는 것이 승인이다 ("승인 1명 필수"는 켜지 않음)
- merge 되면 브랜치 자동 삭제
- 긴급 수정도 같은 길 (`fix/` 브랜치 → PR → CI → merge). 예외 없음

## 7. 한눈에

| 곳 | 모양 | 예시 |
|---|---|---|
| Linear 제목 | `종류(영역): 문장` | `feat(db): eCFR Part 63 원문을 Supabase에 적재` |
| 브랜치 | `종류/suu-번호-영어짧게` | `feat/suu-20-ecfr-ingest` |
| PR 제목 | Linear 제목 + ` (SUU-번호)` | `feat(db): eCFR Part 63 원문을 Supabase에 적재 (SUU-20)` |
| main 커밋 | PR 제목과 동일 | 위와 같음 |

## 8. CI가 검사하는 패턴

```
브랜치:  ^(feat|fix|test|chore|docs)/suu-[0-9]+-[a-z0-9-]+$
PR 제목: ^(feat|fix|test|chore|docs)\((db|rag|backend|frontend|ci)\): .{1,40} \(SUU-[0-9]+\)$
```
