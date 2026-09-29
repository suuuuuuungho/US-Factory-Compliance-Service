---
description: 프로젝트 md를 규칙대로 검사하고 Word·PDF 보고서로 만든다
argument-hint: "(비우면 summary·full 두 파일) 또는 md 경로"
---

대상: $ARGUMENTS

비어 있으면 아래 두 파일이다.

- `[1] docs/1) project/0_Project_summary.md`
- `[1] docs/1) project/1_Project_full.md`

## 먼저 읽기

- `[1] docs/4) workflow/3_doc_rules.md` — md 작성 규칙과 검사 항목(6절)

## 순서

1. 레포 루트에서 실행한다. PDF는 로컬 Word로 만들어서 30초쯤 걸린다.

```
python "[1] docs/4) workflow/report/md_to_docx.py" "[1] docs/1) project/0_Project_summary.md" "[1] docs/1) project/1_Project_full.md"
```

2. 출력을 쉬운 한국어로 정리해 보여 준다.
   - `자동으로 고쳤습니다`: md를 직접 고쳤다. `git diff`로 무엇이 바뀌었는지 한 줄씩 알려 준다.
   - `파일:줄: 메시지`: 사람이 고쳐야 하는 문제다. 줄 번호와 무엇을 고치면 되는지 알려 준다.
   - 문제가 하나라도 있으면 그 파일은 Word를 만들지 않았다고 말하고 멈춘다. md를 대신 고치지 않는다.
3. 성공하면 만든 파일 경로(.docx, .pdf)를 알려 준다. 결과물은 md 옆에 같은 이름으로 생긴다.

## 참고

- Word가 없는 컴퓨터에서는 `--no-pdf`를 붙여 .docx만 만든다.
- Word 모양(글꼴·색·번호)을 바꾸려면 `md_to_docx.py`를 고친다. 설계는 `[5] tickets/5)CI/1_feat/SUU-297.md`.
