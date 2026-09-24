# Federal Register DB 구축 계획

[데이터 명세](<../db overview/Data Specification_v1.md>)에 따라 40 CFR Part 63의 변경 근거를 모은다. `★`는 검색·연결용으로 채택한 원본 필드다. 원본 JSON과 문서는 별도로 보존한다. 운영 수집·메타데이터 적재는 2026-09-21에 실행했다(SUU-210). 자동 갱신(Step.4)은 아직 없다.

## [1] Step.1 수집

1) 1-1. 데이터 Overview
   - 규정 변경 문서에는 제안, 확정, 정정, 공고, 철회·연장 등이 있다. 종류를 먼저 걸러 버리지 않는다.
   - Part 63 구조화 검색을 끝까지 읽은 결과 1,532행이었다. 문서번호는 1,531종이다. 과거 원문과 정정문이 같은 번호를 쓴 실제 사례가 있다.
   - ★ `document_number`, `publication_date`, `html_url`: 문서의 번호·발행일·주소. 실제 `2026-03638`, `2026-02-24`. 세 값을 보존하고 발행일+번호로 식별한다.
   - ★ `title`, `abstract`: 제목과 요약. 예시 문서는 Coal- and Oil-Fired Electric Utility Steam Generating Units의 `Final Repeal` 문서다. 검색에 사용하되 요약을 본문으로 대체하지 않는다.
   - ★ `type`, `action`, `subtype`: 문서 종류·행위·세부 분류. 실제 `Rule`, `Final rule.`, `null`. 제안과 확정을 구분한다.
   - ★ `agencies`: 발행기관 배열. 실제 EPA의 `id=145`, `slug=environmental-protection-agency`. 여러 기관일 수 있다.
   - ★ `cfr_references`: 관련 CFR. 실제 `title=40`, `part="63"`, `chapter=null`, `citation_url=null`. 규정 연결의 첫 단서다.
   - ★ `effective_on`, `dates`: 시행일과 날짜 설명. 실제 `2026-04-27`. 여러 기한이나 일부 조항별 시행일은 `dates`·본문에서 보완한다.
   - ★ `comments_close_on`, `signing_date`: 의견 마감일·서명일. 같은 예시에서는 `null`. 값이 없음을 보존한다.
   - ★ `correction_of`, `corrections`, `disposition_notes`, `not_received_for_publication`: 정정·처리 상태. 예시에서는 `null`, `[]` 등이 있었다. 철회나 대체 여부를 확인하는 보조 근거다.
   - ★ `docket_ids`, `regulation_id_numbers`: 같은 규칙 작업을 묶는 번호. 실제 `EPA-HQ-OAR-2018-0794`, `2060-AW68`. 관련 문서 탐색에 사용한다.
   - ★ `full_text_xml_url`, `body_html_url`, `raw_text_url`, `pdf_url`, `mods_url`: 본문·공식 PDF·서지정보 주소. 제공되는 형식을 확인해 원문과 근거를 확보한다.
   - ★ `public_inspection_pdf_url`: 발행 전 공개본 주소. 예시에도 별도 URL이 존재한다. 발행본과 구분한다.
   - ★ `citation`, `volume`, `start_page`, `end_page`, `page_length`: 인용 위치. 실제 `91 FR 9088`, `91`, `9088`, `9134`, `47`.
   - ★ `images`, `images_metadata`: 수식·그림 자산. 실제 `ER24FE26.031` 이미지가 있었다. 그림으로 된 근거를 보존한다.
   - `topics`, `toc_doc`, `toc_subject`, `significant`: 주제·목차·중요 표시. 예시 `significant=true`. 보조 검색 메타데이터로 보존한다.
   - `dockets`, `regulation_id_number_info`, `regulations_dot_gov_info/url`, `comment_url`: 의견·첨부 연결 정보. 실제 docket 상세에 `supporting_documents_count=776`이 있었다. FR 문서 776건이라는 뜻은 아니다.
   - 대통령 문서 관련 필드와 `page_views`는 원본만 보존한다. 조회수는 규정의 효력 판단에 쓰지 않는다.
   - 출처: [실제 상세 JSON](https://www.federalregister.gov/api/v1/documents/2026-03638.json), [API 안내](https://www.federalregister.gov/developers/documentation/api/v1).

2) 1-2. 수집 방법
   - 작업 위치: `[2] db/2) Federal Register/`. 원본 경로는 `raw/{발행연도}/{발행일}_{문서번호}/{sha256}/`으로 계획한다.
   - 1차 전체 목록: [Part 63 조건 API](https://www.federalregister.gov/api/v1/documents.json?per_page=1000&conditions%5Bcfr%5D%5Btitle%5D=40&conditions%5Bcfr%5D%5Bpart%5D=63&order=oldest). 1994년부터 수집 종료일까지만 대상으로 고정한다.
   - `next_page_url`이 없어질 때까지 따라간다. 반환된 `search_after_cursor`를 버리거나 페이지 번호만 추측해서 만들지 않는다.
   - 목록을 날짜 구간별로 나누면 전체 건수와 고유 문서 키를 대조한다. 겹치는 구간은 근거 있는 중복만 합친다.
   - 2차 보완: EPA 문서에서 `40 CFR 63`, `Part 63`, 관련 규칙명·Subpart 명칭을 검색하고, 확보한 docket/RIN과 eCFR 출처 인용으로 연결 문서를 추가한다.
   - 검색 문구별 결과와 포함 이유를 보존한다. 보완 후보는 `검토 전`으로 두고 본문에서 실제 관련성을 확인한다.
   - 각 문서 상세 JSON의 원문 주소를 사용해 XML → HTML/텍스트 순으로 가용 형식을 확인하고 공식 PDF도 보관한다. 확장자와 실제 형식이 일치하는지 검사한다.
   - 반복 문서번호는 발행일별 원본 URL·GovInfo PDF·MODS를 대조한다. 번호만 받는 상세 API가 어느 발행본을 반환했는지도 확인한다.
   - Public Inspection은 공식 목록에서 별도 수집한다. 확정 발행되면 날짜·번호·제목·내용을 대조해 연결한다. 이번에는 해당 목록 API의 전체 동작 검증을 하지 않았다.

3) 1-3. 수집 관련 유의점
   - API는 인증키 없이 공개되지만 서버의 응답 제한은 따라야 한다. 초기 동시 요청은 호스트당 1개로 둔다.
   - `cfr_references`가 빈 문서도 관련 Notice·연장·철회일 수 있다. 본문·관련 문서 탐색을 생략하지 않는다.
   - 오래된 문서의 XML·정정 연결·일부 날짜가 없을 수 있다. 형식별 확보 상태를 별도로 기록한다.
   - 본문에 적힌 법적 시행일과 API 수집 시각을 구분한다. 서버가 만든 `page_views.last_updated`를 문서 개정일로 쓰지 않는다.

4) 1-4. 수집시 마주한 문제와 해결
   - 실제 `03-5521`은 2003-05-27 Rule과 2003-08-28 Correction에 함께 존재했다. 발행일과 문서번호를 묶어 두 행 모두 보존한다.
   - 목록에 `Uncategorized Document` 51행이 있었다. 알 수 없는 종류를 버리지 않고 원본값과 검토 상태를 남긴다.
   - 예상 원문 링크 실패: PDF나 HTML로 보완하되 출처가 같은 발행본인지 확인한다. 실패 URL은 재시도 목록에 남긴다.
   - 실행(SUU-210)에서 확인: 요청을 하나씩 순서대로 보내면 분당 문서 약 12건, 1,532건 × 3파일에 약 2시간이 걸렸다. 문서 단위로 동시 6개(`--workers 6`)로 바꿔 23분에 끝냈다. 결과와 미확보 목록은 목록 순서 그대로 합친다.
   - 실행에서 확인: HTTP 실패·형식 불일치는 0건이었다. 미확보는 전부 상세 JSON에 주소가 없는 경우(`no url`)였다.

5) 1-5. 수집 결과
   - 조사 완료: 전체 목록 1,532행, 상세 JSON 표본 확인. 목록 종류는 Rule 733, Proposed Rule 720, Correction 28, Uncategorized 51행이었다.
   - 실행 완료(2026-09-21, SUU-210): 조건 `cfr title=40 part=63`, 종료일 2026-09-21, 목록 2쪽, 1,532행 = API 총 건수, 고유 문서 키 1,532(문서번호 1,531종 — `03-5521` 2건). 원본 653 MB.
   - 형식별 확보: 상세 JSON 1,532 / XML 1,185 / PDF 1,486. 미확보 393건은 모두 API에 주소가 없음 — XML 347건(1994년 46·1995년 47·1996년 50·1997년 55·1998년 69·1999년 75·2000년 2·2001년 1·2006년 1·2009년 1), PDF 46건(전부 1994년). 재시도 목록(`retry.jsonl`)은 비어 있다.
   - 보완 후보(2차) 목록 수집은 아직 하지 않았다.

6) 1-6. 수집 한계
   - API의 Part 메타데이터 검색만으로 모든 관련 문서를 보장할 수 없다. 1차 목록 완료와 보완 탐색 완료를 별도로 표시한다.
   - 1994년 이전 자료와 Regulations.gov의 모든 첨부·의견은 이번 기본 수집 범위 밖이다. 필요한 근거가 발견되면 별도 범위로 추가한다.
   - FederalRegister.gov 표시본의 공식 법적 상태와 GovInfo 공식본을 구분한다. [공식 상태 안내](https://www.federalregister.gov/developers/documentation/api/v1)

## [2] Step.2 파서

1) 2-1. 파서 방법
   - 문서를 제목, 요약, 날짜 설명, 배경 설명, 개정 지시, 규정 본문, 표·각주·그림으로 나눈다.
   - XML/HTML의 구조를 우선 사용한다. 읽을 수 있는 텍스트가 없는 PDF는 OCR 대상으로 분리하고 페이지 위치를 보존한다.
   - `40 CFR Part 63`, Subpart, `§ 63.x` 참조를 찾아 원문 문장·블록 위치와 함께 저장한다. 참조가 Part 수준이면 section을 억지로 채우지 않는다.
   - 개정 지시의 추가·수정·삭제·재지정은 원문 위치와 함께 추출한다. ‘언급했다’와 ‘개정했다’를 다른 관계로 둔다.
   - 시행일, 조항별 기한, 의견 마감, 효력 정지·연장·철회는 사건으로 나눈다. 자동 추출값에는 `검토 전/확인됨/불명` 상태를 둔다.
   - docket/RIN을 공유하면 같은 규칙 작업의 후보 관계로 연결한다. 원문 근거 없이 최신 문서가 과거 문서를 전부 대체했다고 판단하지 않는다.

2) 2-2. 파서 관련 유의점
   - Proposed Rule을 현행 규정으로 저장하지 않는다. Rule의 일부가 아직 시행 전일 수도 있다.
   - FR 문서의 개정문을 현재 eCFR 본문에 바로 덮어쓰지 않는다. 해당 기준일 eCFR와 별도로 비교한다.
   - 긴 설명과 짧은 개정 지시를 구분해 보관한다. 수치·단위·예외·각주를 함께 유지한다.

3) 2-3. 파서시 마주한 문제와 해결
   - 조사에서 확인: `effective_on`과 `dates`의 정보량이 다르다. 단일 날짜 외의 설명을 보존하고 적용 범위별 날짜를 추출한다.
   - 조사에서 확인: 그림 자산이 본문 밖에 있다. 이미지 주소·원본 해시를 본문 블록에 연결한다.
   - 실행(SUU-210)에서 확인: 1,532건 파싱에 1초. 보류(held) 0건 — 상세 JSON이 깨졌거나 필수 필드가 빠진 문서는 없었다.
   - 실행에서 확인: docket 식별자는 `dockets[].id`에서 가져온다. `docket_ids`에는 FRL 번호가 섞여 있고 2003년 문서처럼 `"OAR-2002-0040, FRL-7461-4"` 한 문자열로 붙은 경우가 있다. 이 파서(SUU-207)는 메타데이터만 다루며 본문 블록·개정 지시·관계 추출은 아직 없다.

4) 2-4. 파서 합격 기준과 파서 실행 결과
   - 모든 수집 문서가 파싱 성공 또는 사유가 있는 보류 중 하나여야 한다. 조용히 사라진 문서는 0건이다.
   - 모든 근거 블록에 발행일·문서번호·공식 원문 주소·위치가 있어야 한다.
   - 확정·제안·정정·분류 불명·시행일 연장·구형 텍스트·표/그림 포함 문서를 검증 표본에 넣는다.
   - 표본에서 문서 종류·날짜 원문·개정 대상·수치·부정어 누락이 없어야 한다. 확정할 수 없는 시행일은 자동 확정하지 않아야 한다.
   - 같은 원본 재파싱 결과가 같고, `03-5521`의 두 발행본이 모두 남아야 한다.
   - 실행 결과(2026-09-21, SUU-210): 수집 1,532 = 파싱 성공 1,532 + 보류 0. 조용히 사라진 문서 0건. `03-5521`은 2003-05-27 Rule과 2003-08-28 Correction 두 행이 모두 남았다(같은 제목 "Engine Test Cells/Stands"). 재파싱 결과는 같다(jsonl에 release_id·uuid를 넣지 않음).
   - 아직 안 한 것: 본문 블록·개정 지시·수치·부정어 표본 검증(본문 파서가 없음). 시행일은 `effective_on`만 `검토 전`으로 기록했다.

5) 2-5. 파서 결과
   - 실제 산출물(`parsed/2026-09-21/`): `fr_document.jsonl` 1,532 · `fr_identifier.jsonl` 1,453 · `fr_cfr_reference.jsonl` 2,422 · `fr_date_event.jsonl` 662 · `quality_report.json`. 본문 블록·관계(`fr_block`·`fr_relation`)는 이후 티켓.
   - 본문 상태: XML 1,185 · PDF만 301(`pdf_only`) · 둘 다 없음 46(`missing`, 1994년).
   - 원본 날짜 문구와 정규화 날짜, 원본 종류와 서비스 분류를 나란히 저장한다.

6) 2-6. 파서 한계
   - 법원 결정·별도 행정조치 때문에 효력이 바뀔 수 있다. FR 파서만으로 모든 법적 상태를 자동 확정할 수 없다.
   - 과거 문서의 깨진 문자나 OCR 불명 부분은 근거 사용 전에 검토해야 한다.

## [3] Step.3 DB 적재

1) 3-1. DB 적재 방법
   - [eCFR 계획의 공통 테이블](<1_eCFR 구축 계획.md>) `common_ingest_run/common_raw_object/common_dataset_release/common_dataset_current/common_release_object/common_ingest_checkpoint/common_ingest_error/common_change_log`를 공유한다.
   - 원본 저장 → 임시 테이블 적재 → 중복·참조·본문 검사 → 새 FR release 공개 순서다.
   - 새 문서와 수정된 문서는 내용 해시로 찾는다. 새 release의 목록에는 변경 없는 기존 문서도 포함하고 원본 파일은 재사용한다.
   - 원문 근거로 쓰인 과거 release는 유지한다. 전체 최초 수집과 보완 후보 수집은 scope를 구분해 공개 범위를 알 수 있게 한다.

2) 3-2. DB 적재 관련 유의점
   - 식별자·docket·RIN은 문자열이다. `03-5521` 같은 과거 번호를 숫자나 현재 연도 형식으로 바꾸지 않는다.
   - 원문에 없는 날짜·조문·정정 관계는 NULL 또는 검토 상태로 둔다.
   - 공개 트랜잭션 안에서 긴 다운로드나 PDF 추출을 실행하지 않는다.

3) 3-3. DB 적재 시 마주한 문제와 해결
   - 실행(SUU-210)에서 충돌 0건. 발행일+번호 키로 `03-5521` 2건이 나란히 들어갔다.
   - `common_raw_object`는 `(source_url, sha256)` 고유 제약이 있어 다음 as_of 등록 때 같은 원본을 다시 넣으면 터진다. 등록 전에 sha256으로 조회해 이미 있는 행을 재사용한다(SUU-209).
   - 원본 4,203개(상세 1,532·XML 1,185·PDF 1,486)를 한 줄씩 넣지 않고 500행씩 묶어 넣는다.
   - 상세 API가 다른 발행일을 반환하면 연결을 중단하고 해당 발행일의 공식 PDF·MODS를 사용해 검토한다.
   - 조문을 찾지 못한 문서는 삭제하지 않고 미해결 참조로 보관한다.

4) 3-4. DB 적재 실행 결과
   - 실행 완료(2026-09-21 22:44, SUU-210): 등록 → COPY → 검사 → 공개 **33초**. release `a7e01523-f9b2-453d-9250-317db38cd5eb`, `common_dataset_current(fr, part63_metadata)`가 가리키며 status `published`.
   - 표 4개 행 수 = jsonl 행 수: `fr_document` 1,532 · `fr_identifier` 1,453 · `fr_cfr_reference` 2,422 · `fr_date_event` 662. 검사 문제 0건(행 수·고아 FK·`source_object_id` NULL·quality_report 모두 일치).
   - 원본 연결: `source_object_id` NULL 0, `body_object_id` NULL 347(XML 없음), `pdf_object_id` NULL 46 — 수집 미확보 수와 같다.
   - DB 용량 3,110 MB → 3,124 MB (+14 MB). `fr_*` 표·인덱스 10 MB(`fr_document` 9 MB, 나머지 1.6 MB).
   - 아직 안 한 것: 이전 release 복구 시험(release가 하나뿐), 자동 갱신(Step 4).

5) 3-5. 테이블 스키마
   - 공통 PK/FK 뜻과 운영 필드는 eCFR 계획의 3-5절을 따른다. 아래 예시의 값은 위 실제 JSON에서 왔으며 `release_id` 등은 설계 필드다.
   - `fr_document`: `(release_id FK, document_key text) PK`, `publication_date date`, `document_number text`, `canonical_url text`, `title/abstract/type_raw/action/subtype text NULL`, `agencies jsonb`, `citation text`, `volume/start_page/end_page integer NULL`, `source_object_id FK`, `body_object_id/pdf_object_id FK NULL`, `content_hash text`, `raw_metadata jsonb`, `scope_status text`, `body_status text`.
   - `document_key` 설계 예: `2026-02-24/2026-03638`. `(release_id, publication_date, document_number)`에 고유 제약을 두며 충돌은 원문 대조 후 처리한다. Public Inspection에는 아직 이 키가 없을 수 있다.
   - `fr_block`: `(release_id, document_key, block_no integer) PK`, `(release_id, document_key) FK → fr_document`, `kind text`, `heading/text_content/markup text`, `source_locator text`, `page_no integer NULL`, `asset_object_id FK NULL`. 예: DATES 블록과 이미지 `ER24FE26.031`.
   - `fr_cfr_reference`: `reference_id uuid PK`, `(release_id, document_key) FK`, `title integer`, `part/subpart/section/paragraph text NULL`, `relation_type text`, `raw_citation/evidence_locator text`, `review_status text`, `ecfr_release_id/ecfr_node_key NULL`(해결된 경우 ecfr_node의 복합 FK). 실제 `title=40`, `part=63`; Subpart는 본문 추출 전 NULL이다.
   - `fr_date_event`: `event_id uuid PK`, `(release_id, document_key) FK`, `event_kind text`, `event_date date NULL`, `applies_to text NULL`, `raw_text/evidence_locator text`, `review_status text`. 실제 예: `effective`, `2026-04-27`. 날짜별 적용 조항을 따로 둔다.
   - `fr_identifier`: `(release_id, document_key, identifier_kind, identifier_value) PK`, `(release_id, document_key) FK → fr_document`, `identifier_kind text`(docket/RIN), `identifier_value text`. 실제 `EPA-HQ-OAR-2018-0794`, `2060-AW68`.
   - `fr_relation`: `relation_id uuid PK`, `release_id FK`, `from_document_key/to_document_key text`(같은 release의 fr_document에 각각 복합 FK), `relation_type text`, `evidence_locator text`, `review_status text`. 정정·철회·대체·관련 작업을 구분한다. 미수집 상대방은 원문 후보 키로 별도 보류한다.
   - `fr_public_inspection`: `(release_id FK, source_key text) PK`, `source_url/pdf_url text`, `filed_at timestamptz NULL`, `document_number/title text NULL`, `source_object_id FK`, `published_document_key text NULL`, `match_status text`. 이 값은 별도 원본 필드 검증 후 매핑하며 이번 조사에서 실제 예시는 확보하지 않았다.
   - 인덱스: 발행일, 원본 문서번호, CFR title/part/subpart/section, docket/RIN, 각 외래키. 관계를 조회할 때 기준일에 맞는 eCFR release를 명시한다.

## [4] Step.4 갱신되는 데이터 자동 적재

1) 4-1. DB 적재 방법
   - 제안 일정: 매일 04:17 UTC, 한국 13:17. Public Inspection 확인은 같은 실행에서 별도 단계로 둔다.
   - 마지막 성공 이후 구간에 30일을 겹쳐 다시 조회한다. 30일은 우리 초기 운영값이며 완전성 보장은 아니다.
   - 매월 전체 Part 63 목록·기존 문서 메타데이터·docket/RIN 연결을 다시 대조해 오래된 문서의 늦은 정정을 찾는다.
   - 변경을 발견하면 원문 재확보 → 파싱 → 검증 → 새 release → common_change_log 순으로 처리한다.
   - 검토된 시행 예정일은 매일 상태를 다시 확인한다. 날짜 도달만으로 eCFR 본문을 직접 변경하지 않는다.

2) 4-2. DB 적재 관련 유의점
   - 페이지 전체 성공과 검사가 끝난 구간만 checkpoint를 전진시킨다.
   - RIN·docket이 같아도 모든 문서가 같은 규정을 바꾸는 것은 아니다. 자동 연결은 근거와 검토 상태를 포함한다.
   - 공고 목록이 잠시 비어도 기존 문서를 삭제하지 않는다. 정상 전체 응답을 확인한 뒤 미노출 상태를 판단한다.
   - HTTP 재시도·동시 실행 잠금·직전 정상 release 유지·실패 기록은 공통 정책을 사용한다.

3) 4-3. DB 적재 시 마주한 문제와 해결
   - 자동 적재 미실행. 늦은 추가·과거 정정은 겹침 조회와 월간 전체 대조로 발견한다.
   - 동일 URL의 파일 교체는 본문 해시로 발견하고 이전 파일을 유지한다.
   - 잘못된 날짜 추출은 date_event를 검토 전으로 되돌리고 원문 근거를 다시 확인한다.

4) 4-4. DB 적재 실행 결과
   - 미실행. 신규 문서·수정 문서·동일 번호 다른 발행일·철회·시행 연장·중간 페이지 실패·재실행을 검증해야 한다.
   - 완료 조건: 누락된 페이지 0개, 재실행 중복 0개, 제안이 현행 규정으로 표시되는 경우 0개, 변경 근거와 이전 버전 모두 조회 가능.
