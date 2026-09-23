# SUU-46 feat(rag): ADI·CAA 회신 30건으로 RAG 평가 정답지 작성

## 목표
ADI·CAA Dashboard의 Part 63 회신 30건을 사람이 읽어, 질문(시설·공정 설명)과 정답(EPA가 근거로 쓴 Subpart·조문)을 `[6] rag/eval/rag_eval_case.jsonl`에 한 줄씩 적는다. RAG를 만들기 전에 시험지를 먼저 만드는 것이다.

## 건드릴 파일
- 만들 것: `[6] rag/eval/rag_eval_case.jsonl` — 한 줄 = 사례 하나, 30줄 이상. 칸 7개, 이 순서:
  `case_id, question, gold_subparts, gold_citations, source, source_ref, notes`
- 이미 있음 (수정 금지): `[6] rag/tests/test_rag_eval_case.py`, fixture `[6] rag/tests/fixtures/ecfr_part63_index_2026-09-11.json` (SUU-44 결과에서 뽑은 Part 63 Subpart 139개·조문 2,385개, 예약 항목 제외)
- 같이 들어감: `[1] docs/3) rag/2_rag 구축 계획.md` — [8]-3 `source_ref` 칸, [10]-1·[12]-2·[13] 티켓 순서 갱신 (이 브랜치에 이미 반영)

## 안 하는 것
- PDF 파서·OCR 코드, ADI·Dashboard 전체 수집 (뒤 티켓 SUU-47·48)
- `rag_eval_case` 표 적재, 평가 실행 (baseline→rerank 비교는 색인 후)
- `pyproject.toml` 수정 (테스트는 파일만 읽고 import가 없다), `tests/` 아래 수정
- 30건 넘게 채우기. 50개+ 확장은 SUU-49

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 30건 이상, 칸 7개가 이 순서로 모두 채워짐, `source`는 `adi`/`dashboard`, `case_id` 중복 없음 | `test_has_thirty_cases_with_all_fields` |
| 질문에 정답이 안 샘 — `63.숫자` 조문 번호, `Subpart 코드`, 두 글자 이상 코드 단어가 `question`에 없음 | `test_question_does_not_leak_answer` |
| `gold_citations`는 전부 `40 CFR 63.xxxx` (문단 `(a)(1)` 허용) 꼴이고 조문이 fixture에 있음. `gold_subparts`도 fixture에 있음. 주 Subpart(`gold_subparts[0]`) 기준 한 Subpart 최대 3건 | `test_gold_exists_in_part63_and_subparts_spread` |

테스트 파일: `[6] rag/tests/test_rag_eval_case.py`

## Codex 메모
**이번 티켓은 Codex 대신 Claude가 구현한다.** 코드가 아니라 웹·PDF를 읽고 데이터를 쓰는 일이라서다. 아래는 구현자(Claude)용 메모.

### 1. 어디서 고르나
- **CAA Dashboard**: https://www.epa.gov/complying-air-emissions-standards-stationary-sources/epa-determinations-compliance-and — HTML 표 236행 중 `Affected Subpart`가 `Part 63, …`인 132행. 표에서 `Facility Name`·`Title`·`Affected Subpart`·회신 링크(PDF)를 읽는다
- **ADI**: https://cfpub.epa.gov/adi/ — 검색 폼에서 Category `MACT`/`NESHAP`/`GACT`로 조회 → 결과의 `View Details` → `Abstract`(질문+답 요약, 인용 조문 포함) → 원문 링크 `index.cfm?fuseaction=home.dsp_show_file_contents&id=<Control Number>` (확장자는 .cfm이지만 PDF가 온다)
- 두 저장소에서 반반쯤. 같은 문서가 양쪽에 있으면 하나만 쓴다

### 2. 읽는 법
- PDF는 scratchpad에 내려받아 `Read` 도구로 읽는다 (10쪽 넘으면 `pages`로 나눠서). ADI는 Abstract만으로 충분하면 PDF를 안 열어도 된다
- 글자가 안 나오는 스캔본, Part 60/61만 다루는 회신, 인용 조문이 지금 목차(fixture)에 없는 옛 회신은 **건너뛴다**. 따로 기록하지 않는다

### 3. 질문 쓰기 (`question`) — RAG 계획 [10]-1
- 회신의 "요청 내용"만: 시설 종류, 공정, 원료·용제·배출물질, 규모(연간 사용량·처리량), 지역. 영어, 실무자 말투, 2~4문장
- **넣지 않는 것**: EPA의 답, Subpart 코드(`PPPP`), `Subpart …`라는 말, 조문 번호(`63.xxxx`). 테스트가 잡는다
- 예 (M200005, LG Chem Michigan): 원문은 "리튬이온 배터리 전극 공정에 VVVVVV가 적용되나"를 묻고 답은 CCCCCCC·63.11607을 근거로 든다. 질문은 이렇게: `We are building a lithium-ion battery cell plant in Michigan. Electrode slurry mixing uses NMP solvent and the coating lines have thermal dryers. Which NESHAP requirements should we check for this process?` — 코드·조문 번호가 없다

### 4. 정답 쓰기
- `gold_subparts`: 회신이 적용/비적용 판단 **근거**로 쓴 Subpart 코드. **첫 번째 = 질문 대상 주 Subpart** (분산 검사가 이걸 센다). 답이 "VVVVVV 아님, CCCCCCC임"이면 `["VVVVVV", "CCCCCCC"]`처럼 둘 다. Subpart A 조문(63.2 정의 등)을 근거로 썼으면 `"A"`도 넣는다
- `gold_citations`: `40 CFR 63.11607` 꼴. 문단은 회신이 콕 집은 경우만 `40 CFR 63.11607(a)(2)`. 단순 언급("see also")은 뺀다. 최소 1개
- `notes`: EPA 답 한 줄 (적용/비적용 + 이유) + 회신 날짜. 나중에 답변 품질 평가에 쓴다. 예: `Not subject to VVVVVV; electrode coating is not chemical manufacturing. CCCCCCC applies to the paint mixing step. 2020-04-08`

### 5. `case_id` / `source_ref`
- ADI: `case_id = adi-M200005`, `source_ref = M200005`
- Dashboard: `case_id = dashboard-king-systems-2020-06-16` (시설 slug + 회신 날짜), `source_ref = 회신 PDF URL` (Safe Links 풀어서 `epa.gov` 실제 주소)

### 6. 고르는 분산
- 주 Subpart 하나에 최대 3건. 업종을 섞는다: 표면코팅(PPPP·MMMM·KK·RRRR), 화학(FFFF·HHHHH·VVVVVV), 보일러·엔진(DDDDD·JJJJJJ·ZZZZ), 금속(XXXXXX·WWWWWW), 목재·플라스틱(DDDD·WWWW), 정유·저장(CC·EEEE) 등
- "적용됨"만 고르지 않는다. "적용 안 됨"·"일부만 적용" 회신을 3분의 1쯤 넣는다. 검색이 반례도 찾는지 봐야 한다

### 7. 파일 쓰기
- UTF-8, LF, `json.dumps(row, ensure_ascii=False)` 한 줄씩. 키 순서는 위 7개 그대로 (테스트가 `list(case) == FIELDS`로 본다)
- 추가한 순서대로 둔다. 정렬·시각·uuid 없음

### 8. fixture 갱신 (기준일이 바뀔 때만)
```
python "[2] db/pipeline/1_eCFR/ecfr_parse.py" <기준일>
# nodes.jsonl 에서 reserved=false 인 subpart identifier 와 section identifier 를 뽑아
# [6] rag/tests/fixtures/ecfr_part63_index_<기준일>.json 에 {"as_of", "subparts", "sections"} 로 저장
```
지금 fixture는 2026-09-11 기준 (Subpart 139, 조문 2,385).

### 9. 흐름
Claude가 30건 초안 작성 → 사용자가 훑어보고 이상한 것 지적 → 고침 → `python -m pytest` 초록 → Claude가 커밋·PR (제목 = 이 파일 첫 줄 + ` (SUU-46)`) → 사용자 merge
