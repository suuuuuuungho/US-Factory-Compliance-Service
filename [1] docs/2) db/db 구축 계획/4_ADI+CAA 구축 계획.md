# ADI + CAA Dashboard DB 구축 계획

[전수조사 결과](<../db overview/2_db 전수조사 결과.md>)에 따라 EPA의 규정 해석·적용 회신을 모은다. CAA Dashboard는 **EPA Determinations of Compliance and Applicability under CAA 111, 112, and 129**를 뜻한다. ECHO의 Air Dashboard나 CAA Pipeline과는 다른 자료다. `★`는 검색·연결용으로 채택한 원본 필드다. 운영 수집·파싱·DB 적재는 미실행이다.

## [1] Step.1 수집

1) 1-1. 데이터 Overview
   - ADI 전체 목록: 3,825행, 고유 Control Number 3,825개를 직접 확인했다.
   - Dashboard 전체 목록: 236행. Part 63을 명시한 행은 132개이고 해당 Subpart 코드는 37종이었다.
   - 위 수치를 더한 값을 고유 판정 수로 쓰지 않는다. 두 저장소에 같은 문서가 있을 수 있고, 한 문서에 여러 질문·규정이 있을 수 있다.
   - EPA 소개는 ADI와 Dashboard를 2019년 5월로 나누지만 ADI 실제 목록에는 2020년 회신이 있다. 두 목록 전체를 각각 확인한다.
   - 전체 상세·원문을 확보하기 전에는 Part 63 최종 관련 문서 수를 확정하지 않는다.
   - 출처: [EPA 통합 안내](https://www.epa.gov/complying-air-emissions-standards-stationary-sources), [ADI](https://cfpub.epa.gov/adi/), [CAA Dashboard](https://www.epa.gov/complying-air-emissions-standards-stationary-sources/epa-determinations-compliance-and).

2) 1-1. ADI 원본 필드와 실제 값
   - ★ `Control Number`: 문서 이름표. 실제 `M200005`. `ADI:M200005`처럼 출처를 붙여 다른 저장소 번호와 구분한다.
   - ★ `Title`: 회신 제목. 실제 `Applicability Determination for a Lithium Ion Battery Manufacturing Facility`. 검색과 목록 표시에 쓴다.
   - ★ `Letter Date`/`Date`: 회신 날짜. 실제 `04/08/2020`. 원본 문자열과 정규화 날짜를 함께 보존한다.
   - ★ `Categories`/`Category`: 규정 분류. 실제 `MACT, NESHAP`. 복수 분류를 보존한다. GACT와 NESHAP 표기만 있는 Part 63 관련 자료도 확인한다.
   - ★ `Office`/`EPA Office`: 회신 기관. 실제 `Region 5`. 지역·기관 문맥을 제공한다.
   - ★ `Letter Author`/`Author`: 작성자. 실제 `Sara Breneman`. 출처 확인에 쓴다.
   - ★ `Abstract`: 질문과 답 요약. 실제 M200005 요약은 LG Chem Michigan의 공정에 관해 `VVVVVV` 적용 여부를 묻고, 회신의 판단 근거로 `CCCCCCC`와 `40 CFR 63.11607`을 언급한다.
   - ★ `Letter` 또는 원문 링크: 회신 전문. 실제 M200005 원문은 207,639바이트의 PDF였다. 전문과 요약을 구분한다.
   - `Recipient`, `Subparts`, `References`는 공식 가이드의 필드다. 이번 M200005 상세 화면에는 별도 항목으로 표시되지 않았다. 없으면 NULL로 두고, PDF·요약에서 추출한 값은 별도 필드에 둔다.
   - 예: `LG Chem Michigan`을 요약에서 찾았다는 이유만으로 원본 `Recipient` 필드값이라고 저장하지 않는다.
   - 출처: [ADI 필드 안내](https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_users_guide), [M200005 원문 링크](https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id=M200005). 요약은 ADI에서 해당 번호의 ‘View Details’를 선택해 확인했다.

3) 1-1. Dashboard 원본 필드와 실제 값
   - ★ `Facility Name`: 요청 시설·기관 이름. 실제 `King Systems Corporation`. 원본 문자열로 보존한다.
   - ★ `Title`: 회신 제목. 실제 `Applicability Determination for Surface Coating Of Miscellaneous Plastic Parts and Products`. 회신 유형과 검색에 사용한다.
   - ★ `Affected Subpart`: 관련 규정. 실제 `Part 63, PPPP: Surface Coating of Miscellaneous Plastic Parts and Products`. 여러 Part·Subpart를 연결하기 위해 필요하다.
   - ★ `Link to Responses`: 회신 링크와 표시문구. 이 행의 표시값은 `2020-06-16`. 파일명으로 표시된 다른 행도 있으므로 날짜 열이라고 가정하지 않는다.
   - 실제 최종 PDF 주소: [King Systems 회신](https://www.epa.gov/system/files/documents/2022-05/King%20Systems%20Corp%20Response_6-16-20.pdf).
   - 원본 표에 Control Number·작성자·수신자·요약·확정 서명일 열은 없다. 이런 값은 파서가 전문에서 추출한 값으로 구분한다.
   - 표의 마지막 수정일 `September 19, 2025`는 개별 회신의 서명일과 다르다.

4) 1-2. 수집 방법
   - 작업 위치: `[2] db/4) ADI+CAA/`. `raw/adi/`와 `raw/caa_dashboard/`로 원본을 구분하고 각 파일의 해시로 버전을 보관한다.
   - ADI: 공개 검색 폼에서 조건 전체 선택 → 조건 확인 → 결과 제출 → 전체 Control Number 목록 보관 → 상세 메타데이터·원문 수집 순서다.
   - 폼 주소·숨은 필드·세션 값은 그 실행에서 받은 값을 사용한다. 세션이 붙은 URL을 영구 문서 식별자로 쓰지 않는다.
   - 현재 HTML에는 전체 결과가 들어 있지만 화면이 바뀔 수 있다. 서버 총건수와 실제 고유 ID 수를 대조하고, 페이지가 나뉘면 끝까지 이동한다.
   - 공식 선택 다운로드의 `.adi` 텍스트와 개별 회신 파일을 확인한다. 제공되는 원문 형식에 따라 텍스트·HTML·PDF로 분기한다.
   - ADI 상세 메타데이터도 전수 확보한다. Part 63·MACT·GACT·Subpart·인용·요약을 함께 확인하고, 관련성이 불명확한 문서는 원문 확인 대상으로 남긴다.
   - Dashboard: 전체 HTML 표와 모든 회신 링크를 보관한다. 목록의 Part 63 132행을 우선 처리하되 나머지 행도 원문의 Part 63 참조 여부를 점검한다.
   - Safe Links의 `url` 값에서 실제 EPA 문서 주소를 읽고, 원래 주소와 정규화 주소를 함께 보존한다. 허용된 공식 호스트인지 확인한 뒤 파일을 가져온다.
   - 모든 문서의 수집·포함·제외·보류 이유를 목록에 남긴다. PDF를 읽지 못한 문서를 관련 없음으로 처리하지 않는다.

5) 1-3. 수집 관련 유의점
   - 날짜·MACT 분류 하나로만 수집 범위를 자르지 않는다. 2019년 이후 ADI 회신과 복수 분류를 포함해야 한다.
   - 날짜처럼 보이는 파일명, 서버 수정일, 목록 날짜, 실제 서명일을 구분한다.
   - `.cfm` 주소가 실제 PDF를 반환할 수 있다. 확장자가 아니라 Content-Type과 파일 시작부를 확인한다.
   - 초기에는 호스트당 동시 요청 1개, 원문 캐시 사용, 성공한 파일의 재다운로드 최소화로 운영한다. 공식 호출 제한 수치는 확인하지 못했다.

6) 1-4. 수집시 마주한 문제와 해결
   - 공식 소개와 실제 날짜 범위 불일치: ADI에 2020년 회신이 있었다. 두 저장소 전체 목록을 독립적으로 수집한다.
   - 구형 가이드의 100건 페이지 설명과 현재 전체 HTML 제공이 달랐다. 화면 표시 개수가 아니라 전체 고유 ID를 센다.
   - M200005의 `.cfm` 원문 링크는 PDF였다. 텍스트로 바로 해석하지 않고 파일 형식별 처리기를 선택한다.
   - `Westvaco Facility`의 표는 Part 63 AAAAA지만 파일명에는 Part 60이 적혀 있었다. 파일명보다 목록·본문 근거를 우선하고 불일치를 기록한다.
   - 날짜 `12/30/1899`가 있는 구형 항목을 확인했다. 서명일 미확정으로 표시하고 원문 검토 전에는 날짜 검색의 정상값으로 사용하지 않는다.

7) 1-5. 수집 결과
   - 조사 완료: ADI 전체 목록 3,825행, Dashboard 전체 236행, ADI 상세 표본과 PDF 응답 형식.
   - 전체 판정문 전문·첨부의 운영 수집은 미실행이다. ADI와 Dashboard 사이의 실제 중복 수, 최종 Part 63 관련 문서 수는 미확정이다.
   - 구현 후에는 목록 수·상세 성공 수·원문 성공 수·Part 63 포함 수·보류 수·중복 관계 수를 따로 기록한다.

8) 1-6. 수집 한계
   - EPA가 공개하지 않은 개별 회신까지 포함할 수 없다. 공개 저장소의 전수 수집과 모든 EPA 판단의 전수 확보는 다르다.
   - 스캔·재입력·깨진 링크·내용 수정이 있을 수 있다. 목록에 있다고 전문을 확보한 것으로 세지 않는다.

## [2] Step.2 파서

1) 2-1. 파서 방법
   - 목록 파서와 원문 파서를 나눈다. 목록의 원본 필드와 전문에서 뽑은 정보를 섞지 않는다.
   - ADI 텍스트는 문서 경계를 Control Number·헤더로 확인하고, 한 파일에 여러 문서가 있으면 각각 나눈다.
   - HTML은 상세 본문만 읽고 메뉴·폼·스크립트를 제거한다. Abstract의 질문과 답을 별도 블록으로 보존한다.
   - PDF는 페이지별 텍스트를 먼저 추출한다. 글자가 없거나 비정상적으로 깨진 페이지만 OCR하고 결과와 원본 페이지를 대조한다.
   - 전문에서 요청 시설, 공정·설비, 질문, EPA 답, 조건, 예외, 서명일, 작성 기관, 인용 조항을 추출한다. 각 값에 페이지·문단 위치와 확인 상태를 남긴다.
   - 규정 인용은 `title=40`, `part`, `subpart`, `section`, `paragraph`로 나눈다. Part 60의 AAAA와 Part 63의 AAAA는 별개다.
   - 인용 관계를 `질문 대상`, `회신상 적용`, `회신상 비적용`, `정의 인용`, `단순 언급`으로 구분한다. 이는 해당 회신의 내용이며 다른 시설의 적용 판정이 아니다.
   - M200005처럼 질문의 Subpart와 답의 Subpart가 다를 수 있다. 문서에 등장한 모든 규정을 ‘적용됨’으로 저장하지 않는다.
   - 회신 당시 규정과 현재 규정은 별도로 연결한다. 당시 eCFR 본문이 확보되지 않았으면 과거 기준 미확보로 표시한다.

2) 2-2. 파서 관련 유의점
   - 원문·요약·자동 추출값·사람이 확인한 값을 구분한다. 추출한 결론은 근거 문구를 함께 가져야 한다.
   - 부정어, 수치, 단위, 공정 조건, ‘제공된 정보에 따르면’ 같은 제한 문구를 보존한다.
   - 특정 요청에 대한 면제·대체 감시·시험 연장을 일반 규칙으로 바꾸지 않는다.
   - 원문에 철회·수정·대체가 명시된 경우 관계를 기록한다. 명시가 없으면 ‘현재도 유효’라고 자동 확정하지 않는다.

3) 2-3. 파서시 마주한 문제와 해결
   - 조사에서 확인: 상세 화면과 과거 가이드의 필드 구성이 다르다. 없는 필드는 NULL, 본문 추출값은 별도 항목으로 처리한다.
   - 조사에서 확인: PDF 링크와 목록의 날짜·Part 표기가 다를 수 있다. 충돌한 값을 모두 보존하고 근거 페이지 확인으로 해결한다.
   - 운영 PDF/OCR 파서는 미구현이다. 정확도나 전체 OCR 필요 비율은 아직 측정하지 않았다.

4) 2-4. 파서 합격 기준과 파서 실행 결과
   - ADI Control Number와 Dashboard 원본 행이 모두 성공·보류·이유 있는 제외 중 하나에 대응해야 한다.
   - 원문을 확보하지 못한 항목, 텍스트 추출 실패, 날짜 불명, 규정 연결 불명은 품질 보고서에 모두 나타나야 한다.
   - 텍스트형 ADI, PDF형 ADI, 디지털 PDF, 스캔 PDF, 여러 Subpart, 날짜 불일치, 부정 답변, 수정·철회 문서를 검증 표본에 넣는다.
   - 표본에서 질문과 답의 뒤바뀜, 부정어·조건·수치의 누락은 불합격이다. OCR된 중요 값은 원본 페이지로 확인한다.
   - 동일 PDF가 두 목록에 나타나도 원본 출처 둘은 유지하고, 중복 근거 노출을 줄일 수 있어야 한다.
   - 운영 파서 합격 시험은 미실행이다. M200005의 상세 요약과 원문 형식만 확인했다.

5) 2-5. 파서 결과
   - 예정 산출물: `source_entries.jsonl`, `documents.jsonl`, `pages.jsonl`, `blocks.jsonl`, `references.jsonl`, `relations.jsonl`, `quality_report.json`.
   - 본문 추출 상태, OCR 사용 여부, 검토 상태, 원문 페이지를 포함한다. 실제 산출 파일은 아직 없다.

6) 2-6. 파서 한계
   - 스캔이 흐리거나 첨부가 빠지면 핵심 사실을 확정할 수 없다. 검토 전 상태를 유지한다.
   - 유사 판정문은 확인할 질문과 근거를 제공한다. 지금의 다른 공장에 대한 최종 적용 결론은 제공하지 않는다.

## [3] Step.3 DB 적재

1) 3-1. DB 적재 방법
   - [eCFR 계획의 공통 운영 테이블](<1_eCFR 구축 계획.md>)을 공유하고 ADI와 Dashboard의 source를 분리한다.
   - 목록 원본 → 상세 원본 → 회신 파일 → 페이지·블록·규정 연결 → 검사 → 새 release 공개 순서다.
   - 최초에는 두 목록 전체를 보관한다. Part 63 근거 서비스는 전문 확보·품질 검사를 통과한 문서만 사용한다. 미확보 목록도 조회할 수 있게 한다.
   - 같은 원본은 해시로 재사용한다. 같은 URL의 내용이 바뀌면 새 버전으로 보존한다.
   - 원본 ID가 없는 Dashboard는 처음 발견한 정규화 문서 URL에 내부 source_key를 부여한다. 링크가 바뀌면 해시·문서 메타데이터를 대조해 별칭을 연결하고, 불명확하면 새 후보로 남긴다.

2) 3-2. DB 적재 관련 유의점
   - ADI Control Number는 문자열이다. 자리수·숫자 형식을 강제하지 않는다.
   - 파일 해시가 같으면 같은 파일임을 알 수 있지만, 다른 파일이라고 다른 판정이라는 뜻은 아니다. 스캔본·재입력본은 검토 후 같은 문서 관계로 연결한다.
   - 시설 이름만으로 ECHO 시설 ID를 자동 확정하지 않는다. 주소·공식 ID·시설 이력을 추가로 대조한다.
   - 특정 문서의 법적 유효 여부가 확인되지 않았으면 `unknown`을 유지한다.

3) 3-3. DB 적재 시 마주한 문제와 해결
   - 실제 DB 적재 미실행. 예상 중복은 ‘원본 목록 항목’과 ‘회신 문서’를 분리해 해결한다.
   - 서명일을 확정할 수 없으면 원본 날짜 문자열과 날짜 출처를 보존한다. NULL을 임의 날짜로 바꾸지 않는다.
   - 과거 Subpart가 현재 목차에 없으면 과거 참조로 남긴다. 현재 조문에 억지로 연결하지 않는다.

4) 3-4. DB 적재 실행 결과
   - 미실행. 전체 목록 수와 항목 수 일치, 원문·페이지·참조 연결 성공, 중복 출처 보존, 같은 자료 재실행 중복 0을 확인해야 한다.

5) 3-5. 테이블 스키마
   - 아래 UUID·source_key·review_status는 새로 만드는 설계 필드다. 원본 예시는 위 목록·상세 응답에서 확인했다.
   - 테이블 접두사는 `adi_`다. CAA Dashboard 회신도 별도 표를 만들지 않고 같은 `adi_` 표에 `source_system=caa_dashboard`로 들어간다. 접두사 규칙은 [2_rules.md](<../../4) workflow/2_rules.md>) 11절을 따른다.
   - `adi_source_entry`: `(release_id FK, source_system text, source_key text) PK`, `control_number text NULL`, `facility_name/title text`, `categories jsonb`, `office/author/recipient text NULL`, `letter_date_raw/link_text/affected_subpart_raw text NULL`, `abstract text NULL`, `source_url/canonical_url text`, `source_object_id FK`, `scope_status text`. ADI 예: `source_system=adi`, `control_number=M200005`; Dashboard에는 control_number가 없다.
   - `adi_document`: `document_id uuid PK`, `canonical_identity text UNIQUE`, `created_at timestamptz`. 같은 회신의 스캔본·재입력본을 연결하는 내부 이름표다. 동일 판정으로 확인되기 전에는 자동 합치지 않는다.
   - `adi_document_version`: `version_id uuid PK`, `document_id FK`, `object_id FK → common_raw_object`, `sha256 text`, `signed_on date NULL`, `signed_on_raw/date_source text`, `text_content text NULL`, `extraction_method/parser_version text`, `quality_status text`, `legal_status text`. `(document_id, sha256, parser_version)`에 고유 제약. 실제 M200005 파일 해시는 `da3f9387a6c176117448676c5835b280ddadf557cbe92709107587563cfaabc5`다.
   - `adi_entry_document`: `(release_id, source_system, source_key, version_id) PK`, source_entry와 document_version에 FK, `match_method/match_status text`. 한 파일이 두 저장소에 실려도 두 원본 항목을 유지한다.
   - `adi_page`: `(version_id FK, page_no integer) PK`, `text_content text`, `extraction_method text`, `ocr_confidence numeric NULL`, `review_status text`. OCR 도구가 점수를 주지 않으면 임의 점수를 만들지 않는다.
   - `adi_block`: `(version_id, block_no integer) PK`, `page_no integer NULL`, `kind text`, `text_content text`, `source_locator text`, `review_status text`. 질문·답변·조건·서명 블록을 구분한다. 텍스트형 원본에는 page_no가 없을 수 있다.
   - `adi_cfr_reference`: `reference_id uuid PK`, `version_id FK`, `block_no integer`, `raw_citation text`, `title integer NULL`, `part/subpart/section/paragraph text NULL`, `reference_role text`, `evidence_locator/review_status text`, `historical_ecfr_release_id/historical_node_key NULL`, `current_ecfr_release_id/current_node_key NULL`. 해결된 eCFR 연결에는 복합 FK를 둔다. 예: M200005 요약의 `40 CFR 63.11607`.
   - `adi_document_relation`: `(from_document_id FK, to_document_id FK, relation_type) PK`, `evidence_version_id FK`, `evidence_locator text`, `review_status text`. 동일 문서·수정·철회·대체 관계를 저장한다.
   - `adi_facility_candidate`: `(document_id FK, echo_release_id, echo_pgm_sys_id) PK`, `match_evidence text`, `review_status text`, ECHO 시설에 복합 FK. 공식 ID나 주소까지 확인하기 전에는 후보로만 둔다.
   - 인덱스: Control Number, source_key, 서명일, 문서 해시, CFR Part/Subpart/section, 기관, 관계 FK. 외부 링크를 키로 사용할 때 세션 토큰·추적 매개변수는 분리한다.

## [4] Step.4 갱신되는 데이터 자동 적재

1) 4-1. DB 적재 방법
   - 제안 일정: Dashboard는 매주 화요일 05:17 UTC/한국 14:17, ADI는 매월 1일 06:17 UTC/한국 15:17에 전체 목록을 재대조한다.
   - 이 일정은 우리 운영안이다. ADI 구형 가이드의 분기별 갱신 설명을 현재의 보장으로 사용하지 않는다.
   - 목록 ID·정규화 링크·메타데이터 해시를 비교해 추가·수정·미노출을 찾고 바뀐 항목의 상세·원문을 가져온다.
   - 목록이 같아도 원문이 교체될 수 있다. 분기마다 기존 원문 링크·해시를 재검사하는 별도 대조 작업을 둔다.
   - 파싱·품질 검사 후 새 release를 공개하고 `common_change_log`에 변경을 남긴다. 임베딩·검색 색인 갱신은 그 뒤의 작업이다.

2) 4-2. DB 적재 관련 유의점
   - 최근 서명일 이후 자료만 수집하지 않는다. 예전 회신이 늦게 올라오거나 수정될 수 있다.
   - 한 번 사라진 링크는 `unavailable`로 표시하고 기존 파일을 유지한다. 공식 철회 문구가 없으면 법적 철회로 바꾸지 않는다.
   - ADI와 Dashboard의 처리 상태를 각각 기록한다. 한쪽 실패가 다른 쪽의 성공 이력을 덮어쓰지 않게 한다.
   - 요청 재시도·중복 실행 잠금·checkpoint·직전 정상 release 유지 정책은 공통 운영 테이블을 따른다.

3) 4-3. DB 적재 시 마주한 문제와 해결
   - 자동 적재 미실행. 예상 HTML 열 변경은 필수 열 검사와 총건수 대조로 감지한다.
   - URL은 바뀌었지만 파일이 같으면 기존 파일에 새 별칭을 연결한다. 파일도 달라졌으면 새 버전으로 검토한다.
   - OCR 실패·본문 부족·Part 불일치는 공개 근거에서 보류하고 실패 항목만 재실행한다.
   - 잘못된 파서 배포는 이전 parser_version으로 만든 정상 release를 다시 가리키게 한다.

4) 4-4. DB 적재 실행 결과
   - 미실행. 2020년 ADI 자료, 같은 PDF의 이중 출처, 같은 URL의 파일 교체, 날짜 불명, 여러 규정, 질문과 답이 다른 문서, 깨진 PDF 링크를 검증해야 한다.
   - 완료 조건: 원본 목록 대조, 재실행 중복 0, 원문 위치 없는 확정 근거 0, 질문·조건·부정 답변 보존, 실패 후 기존 근거 조회 가능.
