# Data Specification v1

> 우리 서비스가 **실제로 Supabase에 넣어 둔 데이터**를 설명하는 문서예요.
> 처음 온 사람도 이 문서 하나만 읽으면 "무슨 데이터가, 어디에, 얼마나 있고, 뭘 조심해야 하는지" 알 수 있어요.

| | |
|---|---|
| 기준일 | 2026-09-24 (이날 `count(*)`로 직접 셈) |
| 조사 범위 | Supabase `public` 스키마의 표 43개 전부. 로컬 폴더(`[2] db/*/raw`)는 뺐어요 |
| 기계용 명세 | `[2] db/contracts/*.odcs.yaml` (6개 파일). 칸 하나하나의 뜻과 타입은 여기 있어요 |
| 티켓 | SUU-268 |

---

## 1. 한눈에 보기

우리 데이터는 **6묶음**이에요. 표 이름 앞부분(접두사)만 보면 어느 묶음인지 알 수 있어요.

| 묶음 | 표 이름 | 쉬운 말로 | 원본 기준일 | 표 수 | 행 수 |
|---|---|---|---|---:|---:|
| eCFR | `ecfr_*` | 지금 시행 중인 **규정집 원문** | 2026-09-11 | 6 | 75,471 |
| Federal Register | `fr_*` | 규정이 **언제, 어떻게 바뀌었는지** 알리는 관보 | 2026-09-21 | 4 | 6,069 |
| ECHO | `echo_*` | 공장들이 **점검받고, 어기고, 벌금 낸 기록** | 2026-09-17 | 14 | 9,478,231 |
| ADI + CAA | `adi_*` | EPA가 "이 규정이 적용되나요?"에 **직접 답한 편지** | 2026-09-22 | 9 | 17,830 |
| RAG | `rag_*` | 위 자료를 AI가 **검색하기 좋게 자른 조각**과 답변 기록 | - | 2 | 6,206 |
| Common | `common_*` | **언제, 어디서 받았는지** 적어 둔 운영 기록 | - | 8 | 9,842 |
| **합계** | | | | **43** | **9,593,649** |

### 데이터가 흘러가는 길

```
 인터넷 원본 (eCFR · FR · ECHO · ADI)
        │  내려받기
        ▼
 common_raw_object      ← 받은 파일 1개 = 1행 (지문 sha256 포함)
        │  읽어서 표로 만들기
        ▼
 ecfr_* · fr_* · echo_* · adi_*     ← 모든 행에 release_id 가 붙음
        │  잘라서 임베딩
        ▼
 rag_chunk              ← AI가 검색하는 곳
        │
        ▼
 서비스 답변 → rag_answer_log
```

---

## 2. 제일 먼저 알아야 할 것 3가지

### ① release = "한 번에 적재한 묶음"

- 자료를 새로 받을 때마다 새 `release_id`가 생겨요.
- 한 번 공개(`published`)한 release는 **고치지 않아요**. 바뀌면 새 release를 만들어요.
- 그래서 거의 모든 표의 열쇠(PK)에 `release_id`가 들어 있어요.

### ② 최신 데이터는 `common_dataset_current`에서 찾아요

```sql
-- 지금 서비스가 쓰는 eCFR 조문만 보기
select n.*
from ecfr_node n
join common_dataset_current c
  on c.release_id = n.release_id and c.dataset = 'ecfr';
```

지금은 자료마다 release가 1개씩만 있어요. 그래도 **항상 이렇게 걸러 쓰는 습관**을 들여요.

### ③ 원본은 절대 버리지 않아요

- 받은 파일은 `common_raw_object`에 기록해요.
- 표로 뽑지 못한 값은 `raw_metadata`, `attributes`, `raw_dates` 같은 JSON 칸에 그대로 남겨요.
- 헷갈리면 원본을 다시 보면 돼요.

---

## 3. 묶음별 카드

카드마다 순서가 같아요: **한 줄 설명 → 어디서 → 표 → 조심할 점**

### 3-1. eCFR — 지금 시행 중인 규정집

| | |
|---|---|
| 한 줄 설명 | 미국 연방 규정 40 CFR **Part 63**(유해 대기오염물질 규정) 원문 |
| 어디서 | [eCFR API](https://www.ecfr.gov/developers/documentation/api/v1) `full/{date}/title-40.xml?part=63` |
| 원본 기준일 | 2026-09-11 |
| 서비스에서 쓰임 | 답변에 붙는 **근거 조문**이 모두 여기서 나와요 |
| 계약 파일 | `[2] db/contracts/ecfr.odcs.yaml` |

| 표 | 행 수 | 1행은 뭐예요? |
|---|---:|---|
| `ecfr_node` | 3,771 | 목차의 한 칸 (Part 1 · Subpart 158 · 조문 2,473 · 부록 647 · 소제목 492) |
| `ecfr_block` | 71,700 | 조문을 자른 조각 (문단 65,188 · 인용 1,910 · 발췌 1,108 · 그림 1,026 · 제목 996 · 표 784 · 수식 481 · 기타 207) |
| `ecfr_asset` | 0 | 본문 속 그림 파일 — **아직 비어 있음** |
| `ecfr_reference` | 0 | 조문 안의 다른 조문 인용 — **아직 비어 있음** |
| `ecfr_history` | 0 | 개정 이력 — **아직 비어 있음** |
| `ecfr_correction` | 0 | 정정 기록 — **아직 비어 있음** |

**주요 칸**

| 칸 | 뜻 | 예 |
|---|---|---|
| `node_key` | 항목 주소. 표끼리 잇는 열쇠 | `40/63/subpart-A/section-63.1` |
| `node_type` | 항목 종류 | `part` / `subpart` / `section` / `appendix` / `subject_group` |
| `heading` | 제목 | `§ 63.1 Applicability.` |
| `reserved` | 빈 자리(예약) 항목인지 | `true` / `false` |
| `ecfr_block.kind` | 조각 종류 | `paragraph`, `table`, `formula` … |

**⚠️ 조심할 점**

- `XXXXXX`는 **진짜 Subpart 이름**이에요. 빈칸 표시가 아니에요. (예전에 이걸 빈칸으로 착각해서 없는 Subpart를 지어낸 적이 있어요.)
- `node_type = appendix`에는 `Table 1 to Subpart A` 같은 **표도 들어 있어요**. 647개가 다 "부록"은 아니에요.
- 본문은 `paragraph`만 있는 게 아니에요. 표·수식·그림을 빼면 내용이 빠져요.

---

### 3-2. Federal Register — 규정 변경 소식

| | |
|---|---|
| 한 줄 설명 | Part 63을 바꾸는 관보(Federal Register) 문서 목록 |
| 어디서 | [FR API](https://www.federalregister.gov/developers/documentation/api/v1) `conditions[cfr][title]=40&conditions[cfr][part]=63` |
| 원본 기준일 | 2026-09-21 (문서 발행일 범위 1994-01-11 ~ 2026-07-06) |
| 서비스에서 쓰임 | "이 규정이 **언제부터** 바뀌었나?"에 답할 때 |
| 계약 파일 | `[2] db/contracts/fr.odcs.yaml` |

| 표 | 행 수 | 1행은 뭐예요? |
|---|---:|---|
| `fr_document` | 1,532 | FR 문서 1건 (Rule 733 · Proposed Rule 720 · Uncategorized 51 · Correction 28) |
| `fr_identifier` | 1,453 | 문서에 붙은 번호 (RIN 1,144 · Docket 309) |
| `fr_cfr_reference` | 2,422 | 문서가 건드리는 CFR 위치 (지금은 모두 `affects`) |
| `fr_date_event` | 662 | 문서의 날짜 (지금은 모두 `effective` 시행일) |

**주요 칸**

| 칸 | 뜻 | 예 |
|---|---|---|
| `document_key` | 문서 열쇠 = `발행일/문서번호` | `2026-02-24/2026-03638` |
| `type_raw` | 문서 종류 | `Rule`, `Proposed Rule` |
| `publication_date` | 발행일 | `2026-02-24` |
| `effective_on` | API가 준 시행일 | `2026-04-27` |
| `body_status` | 본문 상태 | `xml` 1,185 · `pdf_only` 301 · `missing` 46 |

**⚠️ 조심할 점**

- **문서번호만으로는 1건이 정해지지 않아요.** `03-5521` 하나가 Rule과 Correction 두 행에 쓰였어요. 열쇠는 `document_key`예요.
- `Proposed Rule`(제안)은 **아직 시행 중인 규정이 아니에요**.
- 시행일은 조항마다 다를 수 있어요. `effective_on` 하나만 믿지 말고 `fr_date_event`도 봐요.

---

### 3-3. ECHO — 점검·위반·벌금 기록

| | |
|---|---|
| 한 줄 설명 | EPA 대기(ICIS-Air) 전국 시설 자료 + 점검→위반→처분 연결표(CAA Pipeline) |
| 어디서 | [ECHO 다운로드](https://echo.epa.gov/tools/data-downloads) `ICIS-AIR_downloads.zip`, `pipeline_caa_downloads.zip` |
| 원본 기준일 | 2026-09-17 |
| 서비스에서 쓰임 | "비슷한 공장이 **무엇을 어겨서 얼마를 냈나**?" |
| 계약 파일 | `[2] db/contracts/echo.odcs.yaml` |

| 표 | 행 수 | 1행은 뭐예요? |
|---|---:|---|
| `echo_facility` | 280,071 | 시설 1곳 (55개 주·지역. 가동 중 183,937 · 영구 폐쇄 77,832) |
| `echo_facility_identifier` | 279,995 | 시설 번호 ↔ EPA 통합 번호(FRS) 연결 |
| `echo_industry` | 536,235 | 시설의 산업 코드 (NAICS / SIC) |
| `echo_program` | 458,109 | 시설에 걸린 규제 프로그램 (MACT, NSPS, Title V …) |
| `echo_program_subpart` | 191,226 | 시설에 걸린 Subpart (CFR로 변환 성공 155,395 · 실패 35,831) |
| `echo_code_map` | 306 | ECHO 코드 → CFR Subpart 변환표 (ok 299 · 충돌 7) |
| `echo_pollutant` | 864,562 | 시설이 다루는 오염물질 |
| `echo_activity` | 3,242,036 | 활동 1건 (점검 1,818,484 · 굴뚝시험 655,094 · Title V 인증 490,810 · 비공식처분 173,992 · 공식처분 103,656) |
| `echo_activity_facility` | 3,246,696 | 활동 ↔ 시설 연결 |
| `echo_penalty` | 106,520 | 공식처분의 벌금 금액 |
| `echo_violation` | 102,676 | 위반 1건 (HPV·FRV) |
| `echo_violation_facility` | 102,676 | 위반 ↔ 시설 연결 |
| `echo_pipeline_link` | 67,123 | 점검 → 위반 → 처분을 잇는 한 줄 (연결 성공 58,676 · 실패 8,447) |
| `echo_source_row` | 0 | 읽기 실패한 원본 행 — **비어 있음 = 실패 없음** |

**주요 칸**

| 칸 | 뜻 | 예 |
|---|---|---|
| `pgm_sys_id` | ECHO 시설 번호. ECHO 표끼리 잇는 열쇠 | `0100000009003E0010` |
| `registry_id` | EPA 통합 시설 번호(FRS) | `110070834547` |
| `activity_kind` | 활동 종류 | `inspection` / `stack_test` / `titlev` / `formal` / `informal` |
| `activity_id` | 활동 번호 | (`activity_kind`와 같이 써야 1건) |
| `amount` | 벌금 (달러) | `657412` |

**⚠️ 조심할 점**

- **벌금을 `echo_pipeline_link`에서 더하면 부풀어요.** 같은 처분이 여러 줄에 나와요. 합계는 `echo_penalty`에서 처분 1건당 한 번만 더해요.
- `activity_id`만으로는 1건이 안 정해져요. **항상 `activity_kind`와 같이** 써요.
- `activity_date`에 `0001-01-01`, `8888-01-01` 같은 **가짜 날짜**가 있어요. 빈 날짜도 6,221건 있어요. 기간 통계 전에 걸러요.
- `echo_program_subpart`에서 변환 실패(`unresolved`) 35,831행은 `cfr_subpart`가 비어 있어요. **짐작해서 채우지 않아요.**

---

### 3-4. ADI + CAA Dashboard — EPA 판정 회신

| | |
|---|---|
| 한 줄 설명 | 공장이 "이 규정 우리한테 적용돼요?"라고 물으면 EPA가 답한 편지 모음 |
| 어디서 | EPA ADI(Applicability Determination Index) 목록 + CAA Dashboard 목록, 회신 PDF |
| 원본 기준일 | 2026-09-22 |
| 서비스에서 쓰임 | 비슷한 질문의 **선례**로 보여줘요 |
| 계약 파일 | `[2] db/contracts/adi.odcs.yaml` |

| 표 | 행 수 | 1행은 뭐예요? |
|---|---:|---|
| `adi_source_entry` | 4,061 | 목록의 한 행 (Part 63 후보: ADI 995 + Dashboard 132 = 1,127 · 범위 밖 2,934) |
| `adi_document` | 701 | 회신 문서 1건 (같은 파일은 하나로 합침) |
| `adi_document_version` | 701 | 회신 파일과 뽑은 글자 (ok 683 · 일부 8 · 글자 없음 10) |
| `adi_entry_document` | 701 | 목록 행 ↔ 회신 파일 연결 |
| `adi_page` | 2,333 | PDF 1쪽의 글자 (ok 2,292 · 빈 쪽 41) |
| `adi_block` | 1,960 | 회신을 나눈 조각 (본문 692 · 서명 617 · 질문 237 · 답변 234 · 머리 171 · 조건 9) |
| `adi_cfr_reference` | 7,342 | 회신 안의 CFR 인용 (지금은 모두 `mention` 단순 언급) |
| `adi_facility_candidate` | 31 | 회신 ↔ ECHO 시설 연결 **후보** |
| `adi_document_relation` | 0 | 회신끼리의 관계 (개정·철회) — **아직 비어 있음** |

**⚠️ 조심할 점**

- `adi_document_version.signed_on`(서명 날짜)은 **지금 701건 모두 비어 있어요.** 날짜가 필요하면 `adi_source_entry.letter_date_raw`(원본 글자)를 봐요.
- `legal_status`는 모두 `unknown`이에요. 이 회신이 **지금도 유효한지는 아직 몰라요.**
- Dashboard의 `link_text`는 날짜처럼 보여도 **날짜가 아니에요.**
- `adi_facility_candidate`는 "후보"예요. 확정된 연결이 아니에요.

---

### 3-5. RAG — 검색 조각과 답변 기록

| | |
|---|---|
| 한 줄 설명 | AI가 검색하는 조각(임베딩)과, 서비스가 실제로 답한 기록 |
| 만드는 곳 | `[2] db/pipeline/5_rag/`, `[2] db/pipeline/4_ADI+CAA/letter_chunk.py` |
| 계약 파일 | `[2] db/contracts/rag.odcs.yaml` |

| 표 | 행 수 | 1행은 뭐예요? |
|---|---:|---|
| `rag_chunk` | 6,157 | 검색 조각 1개 (eCFR 5,625 · ADI 532). 모두 `kanon-2-embedder` 1792차원, `embedded` |
| `rag_answer_log` | 49 | 질문 1개와 답 (2026-09-21 ~ 09-23, 비용 합계 약 $1.01) |

**⚠️ 조심할 점**

- 검색할 때는 `common_dataset_current`가 가리키는 release의 조각만 써요.
- `rag_chunk`를 만드는 `create table` 파일이 `[2] db/migrations/`에 **없어요**. (아래 5절)

---

### 3-6. Common — 운영 기록

| | |
|---|---|
| 한 줄 설명 | 모든 묶음이 같이 쓰는 "언제, 어디서, 무엇을 받았나" 장부 |
| 계약 파일 | `[2] db/contracts/common.odcs.yaml` |

| 표 | 행 수 | 1행은 뭐예요? |
|---|---:|---|
| `common_ingest_run` | 4 | 적재 실행 1번 (4묶음 모두 `succeeded`) |
| `common_raw_object` | 4,915 | 받은 원본 파일 1개 (PDF 2,192 · JSON 1,533 · XML 1,186 · 기타 4) |
| `common_dataset_release` | 4 | release 1개 (eCFR·FR·ECHO·ADI 각 1개, 모두 `published`) |
| `common_dataset_current` | 4 | 묶음마다 "지금 쓰는 release" 가리킴 |
| `common_release_object` | 4,915 | release ↔ 원본 파일 연결 |
| `common_change_log` | 0 | release 사이 변경 기록 — **아직 비어 있음** |
| `common_ingest_checkpoint` | 0 | 나눠 받기 진행 위치 — **아직 비어 있음** |
| `common_ingest_error` | 0 | 적재 오류 — **비어 있음 = 오류 없음** |

---

## 4. 표끼리 어떻게 이어지나

```
common_dataset_release ─┬─ ecfr_node ── ecfr_block
                        ├─ fr_document ─┬─ fr_identifier
                        │               ├─ fr_date_event
                        │               └─ fr_cfr_reference ──▶ ecfr_node
                        ├─ echo_facility ─┬─ echo_program ── echo_program_subpart
                        │   (pgm_sys_id)  ├─ echo_pollutant / echo_industry
                        │                 ├─ echo_activity_facility ── echo_activity ── echo_penalty
                        │                 └─ echo_violation_facility ── echo_violation
                        └─ adi_source_entry ── adi_entry_document ── adi_document_version
                                                                       ├─ adi_page
                                                                       ├─ adi_block
                                                                       └─ adi_cfr_reference ──▶ ecfr_node
```

- 묶음을 넘는 다리는 두 개예요: **FR·ADI → eCFR** (`*_node_key`), **ADI → ECHO** (`adi_facility_candidate`).
- 외래키(FK) 69개 전체는 각 YAML의 `relationships`에 있어요.

---

## 5. 지금 알고 있는 문제 (확인 필요)

| # | 무엇 | 왜 문제 |
|---|---|---|
| 1 | `fr_diff` 표가 DB에 **없어요** | `[2] db/migrations/SUU-230_fr_diff.sql` 파일은 있는데 적용이 안 됐어요 |
| 2 | `rag_chunk`의 `create table` 파일이 **없어요** | DB에는 있어요. 새로 만들 때 똑같이 재현하기 어려워요 |
| 3 | 빈 표 9개 | `ecfr_asset`, `ecfr_reference`, `ecfr_history`, `ecfr_correction`, `adi_document_relation`, `common_change_log`, `common_ingest_checkpoint`는 아직 안 채웠어요. `echo_source_row`, `common_ingest_error`는 비어 있는 게 정상이에요 |

### ECHO 원본 CSV보다 표의 행이 적은 이유 (확인 완료)

- ECHO는 **Part 63만 고르지 않고 전국 대기 시설 전부**를 넣었어요. (시설 280,071곳 = 원본 CSV 행 수와 같음)
- 원본 행은 하나도 버리지 않았어요. 11개 파일 모두 `read = ok`, 실패(`held`) 0건이에요.
- 줄어든 이유는 **같은 번호가 여러 줄에 나와서 한 줄로 합쳤기 때문**이에요. (열쇠: `activity_kind + activity_id`, 오염물질은 `pgm_sys_id + pollutant_key`)

| 원본 CSV | 원본 행 | 번호 중복 | 표 행 (= 원본 − 중복) |
|---|---:|---:|---:|
| Title V 인증 | 2,583,180 | 2,092,370 | 490,810 |
| 비공식처분 | 339,879 | 165,887 | 173,992 |
| 오염물질 | 977,624 | 113,062 | 864,562 |

- 근거: `[2] db/3) ECHO/parsed/2026-09-17/report.json`의 `files`, `identifiers`, `duplicates`
- ⚠️ 번호는 같은데 내용이 다른 활동이 50,869건 있어요(`conflicts.echo_activity`). 합칠 때 첫 줄만 남았어요.

---

## 6. YAML 데이터 계약 (Data Contract)

### 무엇인가요?

- **사람용 설명서**는 이 문서예요. **기계용 약속서**는 YAML이에요.
- YAML에는 "이 표에는 이런 칸이 있고, 이 칸은 비면 안 되고, 이 표로 이어진다"가 적혀 있어요.
- 양식은 세계 공통 양식인 **ODCS v3.1.0**(Open Data Contract Standard)을 따라요. PayPal이 만들어 공개했고, 지금은 Linux Foundation이 관리해요. → [bitol-io/open-data-contract-standard](https://github.com/bitol-io/open-data-contract-standard)

### 파일

| 파일 | 표 수 | 칸 수 |
|---|---:|---:|
| `[2] db/contracts/ecfr.odcs.yaml` | 6 | 63 |
| `[2] db/contracts/fr.odcs.yaml` | 4 | 56 |
| `[2] db/contracts/echo.odcs.yaml` | 14 | 133 |
| `[2] db/contracts/adi.odcs.yaml` | 9 | 82 |
| `[2] db/contracts/rag.odcs.yaml` | 2 | 33 |
| `[2] db/contracts/common.odcs.yaml` | 8 | 63 |

### YAML 읽는 법 (예시 하나)

```yaml
- name: activity_id          # 칸 이름
  logicalType: string        # 뜻으로 본 타입 (글자)
  physicalType: text         # DB 실제 타입
  description: ECHO 활동 번호. activity_kind 와 함께 써야 하나로 정해진다
  required: true             # 비면 안 됨
  primaryKey: true           # 열쇠(PK)의 일부
```

- `quality`: 지켜야 할 규칙이에요. `library`는 기계가 검사하는 규칙(예: 표가 비면 안 됨), `text`는 사람이 읽는 주의 문장이에요.
- `customProperties.rowCount`: 기준일(2026-09-24)의 실제 행 수예요.

### 버전 규칙 (Git으로 관리)

| 바뀐 것 | 버전 올리기 | 예 |
|---|---|---|
| 설명 글자만 고침 | 끝자리 | 1.0.0 → 1.0.1 |
| 칸·표 **추가** | 가운데 | 1.0.0 → 1.1.0 |
| 칸·표 **삭제**, 칸 **뜻이 바뀜** | 앞자리 | 1.0.0 → 2.0.0 |

- 표를 바꾸는 migration PR에는 **YAML 수정도 같이** 넣어요.
- 다음 단계(별도 티켓): CI에서 `datacontract test`로 "DB가 YAML과 같은지" 자동 검사.

---

## 7. 숫자를 다시 세는 법

이 문서의 행 수는 아래 SQL로 셌어요. 숫자가 이상하면 다시 돌려 봐요.

```sql
select table_name,
       (xpath('/row/c/text()',
              query_to_xml(format('select count(*) as c from public.%I', table_name), false, true, '')))[1]::text::bigint as rows
from information_schema.tables
where table_schema = 'public' and table_type = 'BASE TABLE'
order by 1;
```

---

## 8. 용어 사전

| 용어 | 쉬운 뜻 |
|---|---|
| CFR | 미국 연방 규정집. Title 40 = 환경 |
| Part 63 | 유해 대기오염물질(HAP) 규정. 업종별로 Subpart가 나뉨 |
| Subpart | Part 안의 업종별 장(章). 예: Subpart DDDDD = 보일러 |
| eCFR | CFR의 온라인판. 매일 갱신 |
| Federal Register (FR) | 미국 정부 관보. 규정이 바뀌면 여기에 먼저 나옴 |
| Rule / Proposed Rule | 확정 규칙 / 제안(아직 시행 전) |
| Docket, RIN | 규칙 제정 서류철 번호, 규칙 고유 번호 |
| ECHO | EPA의 점검·위반·처분 공개 시스템 |
| ICIS-Air | ECHO 안의 대기 분야 자료 |
| HPV / FRV | 중대 위반 / 연방 보고 대상 위반 |
| Title V | 큰 공장이 받아야 하는 대기 운영 허가 |
| ADI | EPA 적용 판정 회신 모음 |
| release | 한 번에 적재한 데이터 묶음. 공개 후 고치지 않음 |
| PK / FK | 열쇠 칸 / 다른 표를 가리키는 칸 |
| 임베딩 | 글을 숫자 벡터로 바꾼 것. 뜻이 비슷한 글을 찾을 때 씀 |
| Data Contract | "이 데이터는 이런 모양이다"라는 기계용 약속서 |
