# eCFR DB 구축 계획

이 문서는 [전수조사 결과](<../db overview/2_db 전수조사 결과.md>)를 바탕으로 만든 실행 계획이다. 규정 범위는 40 CFR Part 63 전체다. `★`는 검색·연결용으로 채택한 원본 필드다. 나머지 원본도 파일 그대로 보존한다. 아래 DB 구조는 PostgreSQL 기준 설계안이며 실제 적재는 미실행이다.

## [1] Step.1 수집

1) 1-1. 데이터 Overview
   - 규정집의 ‘목차’와 ‘본문’을 함께 가져온다. 일부 업종이나 적용 조항만 먼저 골라 버리지 않는다.
   - 조사 기준일 `2026-09-10`: subpart 158개, section 2,473개, appendix 종류 647개, subject group 492개. 예약 항목과 표를 포함한 원본 노드 수다.
   - 실제 전체 XML에 표 784개, 이미지 태그 1,511개, 수식 태그 482개가 있었다. 글자만 모으면 근거가 빠진다.
   - ★ `number`, `name`: 규정집 번호·이름. 실제 `40`, `Protection of Environment`. 다른 규정집과 구분한다.
   - ★ `up_to_date_as_of`: 반영 완료 기준일. 실제 `2026-09-10`. 수집 날짜와 구분한다.
   - ★ `latest_amended_on`, `latest_issue_date`: 실질 변경일·발행 변경일. Title 40의 실제 값은 모두 `2026-09-09`. Part 63 자체 변경일로 복사하지 않는다.
   - ★ `meta.import_in_progress`: 정부의 반영 작업 진행 여부. 실제 `false`. 진행 중 자료를 완성본으로 공개하지 않기 위해 필요하다.
   - ★ `identifier`, `type`, `children`: 항목 번호·종류·하위 항목. 실제 `63.1`, `section`. 부모와 자식의 순서를 보존한다.
   - ★ `label`, `label_level`, `label_description`: 원문 제목. 실제 `Subpart A—General Provisions`. 검색 제목과 계층을 만든다.
   - ★ `reserved`: 예약 여부. 실제 Subpart K는 `true`. 본문이 없는 정상 항목을 오류와 구분한다.
   - `volumes`, `size`, `descendant_range`, `received_on`: 인쇄본 권·제공 크기·범위·수신 시각. 실제 Part 63 범위는 `63.1 – 63.12099`. 원본 메타데이터로 보존하고 법적 시행일로 쓰지 않는다.
   - ★ XML `N`, `TYPE`, `HEAD`: 조문 번호·종류·제목. 실제 `N="63.1"`, `TYPE="SECTION"`, `§ 63.1 Applicability.`. 인용 위치를 만든다.
   - ★ `P`, `TABLE`, `img`, `MATH`, 각주·목록·주석 태그: 근거 본문. 실제 첫 문단에 `(a) General. (1)`이 함께 들어간다. 원문 순서를 지킨다.
   - ★ `AUTH`, `SOURCE`, `CITA`, `EDNOTE`: 법적 근거·출처·개정 인용·편집자 주. 실제 전체 XML에 `AUTH` 1개, `CITA` 1,910개가 있었다. 본문과 출처 설명을 구분해 보존한다.
   - ★ 이력 `date`, `amendment_date`, `issue_date`, `substantive`, `removed`: 버전 시점·실질 변경·삭제 정보. 실제 과거 항목에 `amendment_date=2016-12-22`, `issue_date=2018-01-12`, `substantive=false`가 함께 존재한다.
   - 출처: [전체 XML](https://www.ecfr.gov/api/versioner/v1/full/2026-09-10/title-40.xml?part=63), [목차](https://www.ecfr.gov/api/versioner/v1/structure/2026-09-10/title-40.json), [날짜 설명](https://www.ecfr.gov/reader-aids/ecfr-developer-resources/understanding-ecfr-dates).

2) 1-2. 수집 방법
   - 작업 위치: `[2] db/1_eCFR/`. 원본은 `raw/{기준일}/{sha256}/`, 파서 결과는 `parsed/{기준일}/{parser_version}/`에 저장하는 계획이다.
   - 제목 API에서 Title 40의 반영 완료일을 읽는다. PC의 오늘 날짜를 XML 기준일로 바로 넣지 않는다.
   - 같은 기준일의 Title 40 목차에서 Part 63 가지 전체를 찾고, Part 63 XML 전체를 가져온다.
   - HTTP 요청에 `Accept-Encoding: gzip`을 사용하고 실제 응답 헤더에 맞게 압축을 푼다.
   - 이력 API는 응답의 페이지 안내를 확인해 끝까지 읽는다. 제목 정정 목록은 Part 63 참조를 가진 항목만 연결한다.
   - XML이 참조하는 이미지·수식 파일 주소도 모은다. URL별 중복은 줄이되 조문별 연결은 모두 남긴다.
   - 처음에는 현재 원문과 전체 이력 목록을 구축한다. 과거 본문은 ADI 회신일·FR 비교에 필요한 기준일부터 되짚어 수집하고, 확보하지 않은 날짜를 표시한다.
   - 출처 경로: [제목 API](https://www.ecfr.gov/api/versioner/v1/titles.json), [이력 API](https://www.ecfr.gov/api/versioner/v1/versions/title-40.json?part=63), [정정 API](https://www.ecfr.gov/api/admin/v1/corrections.json?title=40).

3) 1-3. 수집 관련 유의점
   - 각 요청의 원본 주소·최종 주소·HTTP 상태·형식·바이트·해시·수집 시각을 남긴다. HTTP 200이어도 접근 확인 HTML이면 XML 성공으로 세지 않는다.
   - 목차에 없는 Subpart 이름을 추측해 만들지 않는다. `ZZ-BBB` 같은 예약 범위 이름을 그대로 보존한다.
   - `appendix`에는 Table도 포함된다. Part 바로 아래 부록과 Subpart 아래 표를 모두 찾는다.
   - 수집 전후 제목 API의 기준일·반영 상태를 비교한다. 도중 원본이 바뀌면 해당 실행을 보류하고 같은 기준으로 다시 수집한다.
   - 요청 제한 수치는 확인되지 않았다. 처음에는 호스트당 동시 요청 1개로 시작하며 429의 `Retry-After`를 따른다.

4) 1-4. 수집시 마주한 문제와 해결
   - 실제 HTTP 406: 압축 허용 헤더 누락. `gzip` 허용과 압축 해제로 해결해 전체 XML을 읽었다.
   - 개발자 설명 페이지가 접근 확인 화면으로 바뀌는 경우를 확인했다. 최종 URL과 응답 형식을 검사한다. 지속 차단은 자동 재시도를 멈추고 운영 오류로 남긴다.
   - 예상 문제: 중간 다운로드 종료. 임시 파일을 검증한 뒤 완성 파일로 바꾸고, 실패 파일은 공개하지 않는다.

5) 1-5. 수집 결과
   - 조사용 읽기 성공: 현재 Part 63 XML 26,332,596바이트와 전체 목차.
   - 조사용 원문 해시: `f381f62280ce8f60d60e28bc9d192155d051e575502e78f6e48f869f180de13c`.
   - 운영용 원본 보관·첨부 전체 다운로드·수집 명세 파일 생성은 미실행이다.
   - 구현 후 결과에는 기준일, 기대/실제 노드 수, 첨부 성공/실패 수, 원본 해시, 실행 ID를 남긴다.

6) 1-6. 수집 한계
   - 현재 원문과 개정 이력만으로 모든 과거 시점의 본문이 확보되는 것은 아니다.
   - Part 63이 인용하는 다른 Part·외부 표준은 참조 목록으로 남긴다. 외부 전문이 없으면 ‘본문 미확보’를 표시한다.
   - Part 63 자료만으로 주정부 허가 조건까지 모두 다뤘다고 표시하지 않는다.

## [2] Step.2 파서

1) 2-1. 파서 방법
   - 파서는 원문을 ‘번호가 붙은 작은 칸’으로 나누는 작업이다. 외부 엔터티·외부 DTD 로딩을 끈 XML 파서를 사용한다.
   - `TYPE`과 부모 관계로 Part → Subpart → 중간 제목 → 조문·표·부록을 순서대로 읽는다. 조문이 항상 같은 깊이에 있다고 가정하지 않는다.
   - 항목의 전체 XML과 순서 있는 본문 블록을 보존한다. 상위 항목의 검색 본문에 자식 전체를 다시 복사하지 않는다.
   - 문단·목록·정의·표·각주·수식·이미지·출처·편집자 주를 종류별 블록으로 만든다. 모르는 태그도 원문과 경고를 남긴다.
   - `(a)`, `(1)`, `(i)`는 문맥을 보고 위치 후보를 만든다. 하나의 P에 여러 번호가 있거나 로마 숫자가 모호하면 원문 블록 위치를 유지하고 검토 대상으로 둔다.
   - 표의 병합 셀, 행·열 제목, 각주 참조를 보존한다. 수치·단위·부등호를 요약문으로 대체하지 않는다.
   - 조문 인용은 원문 문자열과 위치를 보존하고 `title/part/subpart/section/paragraph`로 분리한다. 연결할 대상이 없으면 미해결 참조로 남긴다.
   - XML 링크의 `_SUBSTITUTE_DATE_`는 실제 기준일로 치환한다. 현재 링크와 기준일 고정 링크를 따로 만든다.

2) 2-2. 파서 관련 유의점
   - 규정의 적용·예외·정의·General Provisions 연결은 같은 근거 묶음에서 찾을 수 있어야 한다.
   - 파서 단계에서 법적 적용 여부를 결정하거나 내용을 새로 쓰지 않는다. 원문과 추출한 구조만 저장한다.
   - 예약 항목, 빈 문단, 실제 추출 실패를 서로 다른 상태로 둔다.

3) 2-3. 파서시 마주한 문제와 해결
   - 조사에서 확인: 표가 `DIV9 TYPE=APPENDIX` 안에 있고 본문 밖에도 존재한다. Part 전체의 모든 노드를 순회한다.
   - 조사에서 확인: `P`만으로는 표·수식·이미지를 보존할 수 없다. 블록 종류별 처리와 원문 XML 보관을 함께 한다.
   - 운영 파서는 아직 구현하지 않았다. 실제 파서 오류율을 계산하지 않았다.

4) 2-4. 파서 합격 기준과 파서 실행 결과
   - 해당 실행의 목차 대비 Part·Subpart·조문·부록·중간 제목 수가 100% 일치한다. 이번 기준값을 영구 고정하지 않는다.
   - 원문 태그와 산출 블록을 대조해 설명 없이 사라진 표·이미지·수식·각주가 0개여야 한다.
   - 모든 본문 블록에 부모 항목, 원문 순서, 출처 파일, 원문 위치가 있어야 한다.
   - 보통 조문·예약 조문·Part 부록·Subpart 표·병합 표·수식·중첩 번호를 각각 포함한 검증 문서를 원문과 비교한다. 수치·부정어·예외 문구의 누락은 불합격이다.
   - 같은 원문과 같은 파서 버전으로 두 번 실행했을 때 블록 ID와 내용 해시가 같아야 한다.
   - 조사에서는 XML을 읽고 구조 개수를 대조했다. 위 운영 파서 합격 시험은 미실행이다.

5) 2-5. 파서 결과
   - 예정 산출물: `nodes.jsonl`, `blocks.jsonl`, `references.jsonl`, `assets.jsonl`, `quality_report.json`.
   - 각 레코드는 원본 해시·기준일·파서 버전으로 되짚을 수 있어야 한다. 실제 산출 파일은 아직 없다.

6) 2-6. 파서 한계
   - 이미지를 설명하는 글이 없을 수 있다. 원본 연결을 유지하고 필요할 때 OCR·사람 확인을 추가한다.
   - 정규식으로 찾은 조문 참조나 문단 경로는 법적 관계의 확정 판정이 아니다.

## [3] Step.3 DB 적재

1) 3-1. DB 적재 방법
   - 원본 파일은 파일 저장소, 검색·관계 정보는 PostgreSQL에 둔다. 대형 원본을 모든 행에 반복 저장하지 않는다.
   - 실행 기록 생성 → 원본 보관 → 임시 적재 → 구조·연결 검사 → 정상 묶음 공개 순서로 진행한다.
   - `COPY FROM STDIN`으로 임시 테이블에 묶어 넣는다. 작은 메타데이터는 고유키를 기준으로 `ON CONFLICT` 처리한다.
   - 공개 시 `common_dataset_current`가 가리키는 release만 짧은 트랜잭션에서 바꾼다. 사용자는 완성된 묶음을 읽는다.
   - 동일 원본 해시·파서 버전·범위는 기존 성공 결과를 재사용한다. 파서가 달라지면 같은 원문이라도 새 release로 검증한다.
   - 출처: [PostgreSQL COPY](https://www.postgresql.org/docs/current/sql-copy.html), [INSERT](https://www.postgresql.org/docs/current/sql-insert.html).

2) 3-2. DB 적재 관련 유의점
   - 아래 `PK`는 고유 이름표, `FK`는 다른 테이블의 이름표를 가리키는 연결이다.
   - 날짜는 `date`, 관찰 시각은 UTC `timestamptz`, 인용 번호는 `text`, 상태는 허용값을 제한한 `text`를 사용한다.
   - 부모 연결·조문 경로·release 조회에 인덱스를 둔다. 잘못된 부모나 중복 경로는 공개 전에 차단한다.
   - 읽기 계정과 적재 계정을 구분한다. 비밀번호·연결 문자열은 환경변수로 관리하며 문서·로그에 쓰지 않는다.
   - 원문 근거로 사용된 버전은 유지한다. 이전 release를 지우는 자동 작업은 별도로 설계하기 전에는 만들지 않는다.

3) 3-3. DB 적재 시 마주한 문제와 해결
   - 실제 DB 적재 문제는 아직 없다. 운영 DB 접속 및 적재를 실행하지 않았기 때문이다.
   - 예상 중단: 일부 테이블만 들어감 → release를 `staging/failed`로 유지하고 직전 정상 release를 계속 제공한다.
   - 예상 중복: 재실행 → 원본 해시와 고유키로 같은 자료를 두 번 만들지 않는다.

4) 3-4. DB 적재 실행 결과
   - 미실행. 다음을 기록해야 완료다: 적재 전후 건수, 중복 0개, 고아 연결 0개, 조문 조회 성공, 실패 주입 후 이전 release 유지, 같은 실행 재시도 결과.

5) 3-5. 테이블 스키마 — 네 데이터셋 공통
   - 아래 공통 운영 필드는 새로 만드는 설계다. UUID·상태·경로 예시는 실제 적재값이 아닌 설명용이다.
   - `common_ingest_run`: `run_id uuid PK`(실행 이름표), `dataset text`(예: `ecfr`), `scope jsonb`(예: title 40/part 63), `status text`(running/succeeded/failed/no_change), `started_at/finished_at timestamptz`, `counts jsonb`(수집·적재·보류 수), `error_summary text`.
   - `common_raw_object`: `object_id uuid PK`, `run_id FK → common_ingest_run`(최초 확보 실행), `source_url/final_url text`, `storage_uri text`, `sha256 text`, `byte_size bigint`, `media_type text`, `fetched_at timestamptz`, `source_modified_at timestamptz NULL`, `etag text NULL`. `(source_url, sha256)`에 고유 제약을 둔다. 예: XML URL과 이번 조사 해시. 같은 URL·해시의 파일은 재사용하고 재확인 시각은 실행 기록에 남긴다.
   - `common_dataset_release`: `release_id uuid PK`, `dataset text`, `scope_key text`, `run_id FK`, `source_as_of date NULL`, `manifest_hash text`, `parser_version text`, `status text`(staging/validated/published/failed), `published_at timestamptz NULL`. 동일 dataset/scope/manifest/parser 조합에 고유 제약을 둔다.
   - `common_dataset_current`: `(dataset, scope_key) PK`, `release_id FK → common_dataset_release`, `last_checked_at timestamptz`, `latest_source_as_of date NULL`. 예: `ecfr`, `40/63`이 현재 공개 묶음을 가리킨다. 내용이 같아 새 release를 만들지 않아도 마지막 확인 시각과 원본 반영 기준일은 기록한다.
   - `common_release_object`: `(release_id FK, object_id FK) PK`, `role text`. 한 release에서 사용한 XML·JSON·PDF·ZIP을 빠짐없이 연결한다.
   - `common_ingest_checkpoint`: `(dataset, scope_key, partition_key) PK`, `cursor jsonb`, `completed_run_id FK`, `completed_at timestamptz`. 예: FR의 날짜 구간과 next_page_url. 실패한 페이지를 성공한 위치로 기록하지 않는다.
   - `common_ingest_error`: `error_id uuid PK`, `run_id FK`, `object_id FK NULL`, `record_locator text`, `stage/error_code/message text`, `retryable boolean`, `resolved_at timestamptz NULL`. 예: `ICIS-AIR_FACILITIES.csv:2`와 잘못된 날짜.
   - `common_change_log`: `change_id uuid PK`, `event_key text UNIQUE NOT NULL`, `run_id FK`, `dataset/source_key/change_type text`, `old_release_id FK NULL`, `new_release_id FK`, `old_hash/new_hash text NULL`, `detected_at timestamptz`, `delivery_status text`. dataset·source_key·이전/다음 release·변경 종류를 일정한 형식으로 묶은 해시를 event_key로 사용한다. 이전 값이 없는 초기 수집도 해시 입력에 `baseline`을 넣어 동일 이벤트가 반복 생성되지 않게 한다.

6) 3-5. 테이블 스키마 — eCFR 전용
   - `ecfr_node`: `(release_id FK, node_key text) PK`, `parent_key text NULL`(같은 release의 node를 가리키는 복합 FK), `node_type text`, `identifier text`, `heading text`, `reserved boolean`, `sort_order integer`, `source_object_id FK`, `source_locator text`, `xml_fragment text`, `content_hash text`.
   - `node_key` 설계 예: `40/63/subpart-A/section-63.1`. 부록·중간 제목은 전체 부모 경로를 포함해 같은 제목의 충돌을 막는다. 실제 원본 값은 `identifier=63.1`, `node_type=section`이다.
   - `ecfr_block`: `(release_id, node_key, block_no integer) PK`, `(release_id, node_key) FK → ecfr_node`, `kind text`, `label_path text[] NULL`, `text_content text`, `markup text`, `source_locator text`, `parse_status text`. 예: `(a)` 문단, 표, 수식 블록. `label_path`는 추출값임을 표시한다.
   - `ecfr_reference`: `reference_id uuid PK`, `(release_id, node_key, block_no) FK → ecfr_block`, `raw_citation text`, `target_title integer NULL`, `target_part/target_subpart/target_section/target_paragraph text NULL`, `target_node_key text NULL`, `resolution_status text`, `evidence_locator text`. 예: 첫 문단의 `§ 63.2`.
   - `ecfr_asset`: `(release_id, node_key, block_no, asset_no) PK`, `(release_id, node_key, block_no) FK → ecfr_block`, `source_url text`, `object_id FK → common_raw_object NULL`, `fetch_status text`. 다운로드가 안 된 이미지도 연결 자체는 남긴다.
   - `ecfr_history`: `history_key text PK`(정규화한 원본 이력의 해시), `source_object_id FK`, `identifier/type/title/part/subpart text`, `date/amendment_date/issue_date date`, `substantive/removed boolean`, `raw_metadata jsonb`. 단순히 조문번호와 날짜 하나만으로 중복 제거하지 않는다.
   - `ecfr_correction`: `correction_id text PK`(원본 id), `source_object_id FK`, `cfr_references jsonb`, `corrective_action text`, `error_occurred/error_corrected/last_modified date NULL`, `fr_citation text NULL`, `raw_metadata jsonb`. Part 63 연결만 서비스 범위에 넣는다.
   - 법적 시행 기간을 원본 근거 없이 만들어 저장하지 않는다. release의 관찰 시점과 FR에서 검토한 시행일은 별개다.

## [4] Step.4 갱신되는 데이터 자동 적재

1) 4-1. DB 적재 방법
   - 제안 일정: 매일 03:17 UTC, 한국 12:17. 매주 같은 시간에 전체 대조를 추가한다. 정부의 공식 갱신 시각이 아닌 우리 운영 시간이다.
   - `titles → versions/corrections → Part 63 목차·원문 → 해시 비교 → 파싱·검사 → 적재·공개` 순서다.
   - 최신 실질 개정일만 비교하지 않는다. 비실질 변경·과거 정정과 전체 원문 해시를 함께 본다.
   - 변경 없으면 `no_change`와 마지막 확인 시각을 기록한다. 새 근거가 생기면 `common_change_log`를 남겨 후속 검색 색인을 갱신할 수 있게 한다.
   - 실행 환경은 하나의 스케줄러로 통일한다. 저장소에서 운영한다면 `.github/workflows/db-refresh.yml`을 구현 단계에 추가하고 수동 재실행 입력도 제공한다.

2) 4-2. DB 적재 관련 유의점
   - 같은 dataset/scope의 동시 실행을 잠근다. 종료 전에 다음 실행이 시작돼도 두 release가 서로 덮어쓰지 않아야 한다.
   - 수집·파싱은 공개 트랜잭션 밖에서 수행한다. 공개 포인터 변경과 변경 기록 확정만 짧은 트랜잭션으로 묶는다.
   - 오래된 자료라도 ‘최근 확인 성공’과 ‘원본의 반영 기준일’을 별도로 표시한다.
   - 로그에는 성공/실패·변경 없음·기준일·처리 건수·보류 이유를 남긴다. 외부 메시지 전송은 별도 설정 대상이다.

3) 4-3. DB 적재 시 마주한 문제와 해결
   - 자동 적재는 미실행이다. 다음은 예방 계획이다.
   - 429·일시적 5xx·네트워크 오류: `Retry-After` 우선, 그 외 1·2·4·8·16분 간격으로 최대 5회 재시도 후 실패 기록.
   - 403·접근 확인 화면: 무한 반복하지 않고 운영 점검 대상으로 둔다.
   - 새 태그·노드 급감·부모 연결 오류: 새 release 공개 보류, 원본과 오류 보존, 파서 보완 후 같은 원본으로 재실행.
   - 잘못된 release 공개: 직전 정상 `release_id`로 포인터를 되돌린다. 원본·이력·실패 기록은 유지한다.

4) 4-4. DB 적재 실행 결과
   - 미실행. ‘최초 실행 → 변경 없음 → 실제 변경 → 다운로드 실패 → 파서 실패 → 중간 중단 후 재실행 → 되돌리기’를 검증한 뒤 자동화 완료로 기록한다.
   - 최종 완료 조건: 전체 목차 대조 통과, 재실행 중복 0개, 실패 때 기존 조회 유지, 변경된 근거의 이력 추적 가능.
