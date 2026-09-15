# ECHO DB 구축 계획

[전수조사 결과](<../db overview/2_db 전수조사 결과.md>)를 바탕으로 시설·점검·위반·처분을 연결한다. 기본 수집은 전국 ICIS-Air 10개 CSV와 CAA Pipeline 1개 CSV다. 서비스 조회에서 Part 63·제조업 후보를 구분한다. `★`는 검색·연결용 채택 필드이며, 모든 원본 열은 보존한다. 실제 DB 적재는 미실행이다.

## [1] Step.1 수집

1) 1-1. 데이터 Overview
   - ICIS-Air 전체: 7,513,497행. 시설 280,071행, 프로그램 458,110행, Subpart 191,226행, 오염물질 977,624행, 점검 1,819,117행, 배출시험 655,094행, 인증 2,583,180행, 공식처분 106,520행, 비공식처분 339,879행, 위반 102,676행이다.
   - Pipeline: 67,123행. 사건을 서로 잇는 행 수이며 시설 수나 위반 수와 다르다.
   - 아래 값은 각 CSV 첫 행을 읽은 실제 예시다. 파일마다 다른 시설·사건이므로 예시끼리 연결하면 안 된다. 빈 문자열 `""`도 실제 원본값이다.
   - 전체 파일별 건수·기준 시각·해시는 전수조사 문서의 ECHO 절에 있다.

2) 1-1. 시설 파일의 원본 필드
   - ★ `PGM_SYS_ID`: CAA 시설 번호. `0100000009003E0010`. 모든 자식 자료를 연결한다.
   - ★ `REGISTRY_ID`: EPA 공통 시설 번호. `110070834547`. FRS와 연결한다. 위 번호와 같은 번호가 아니다.
   - ★ `FACILITY_NAME`: 이름. `HIGHLAND PARK MARKET`. 검색과 원문 표시용이다.
   - ★ `STREET_ADDRESS`, `CITY`, `COUNTY_NAME`, `STATE`, `ZIP_CODE`, `EPA_REGION`: 위치. 각각 `68 BRIDGE ST `, `SUFFIELD`, `Hartford`, `CT`, `06078`, `01`. 주소 비교와 지역별 조회에 쓴다.
   - ★ `SIC_CODES`, `NAICS_CODES`: 업종 코드. `""`, `445110`. 제조업 후보 표시의 보조 단서다. 코드가 없다고 제외하지 않는다.
   - ★ `FACILITY_TYPE_CODE`, `AIR_POLLUTANT_CLASS_CODE`, `AIR_POLLUTANT_CLASS_DESC`: 시설·배출원 분류. 이 예시에서는 모두 `""`. 신고된 규모와 빈값을 보존한다.
   - ★ `AIR_OPERATING_STATUS_CODE`, `AIR_OPERATING_STATUS_DESC`: 가동 상태. 이 예시에서는 `""`. 폐쇄 여부와 자료 없음은 구분한다.
   - ★ `CURRENT_HPV`: 현재 고우선순위 위반 표시. `No Violation Identified`. 이 문구를 모든 법 준수의 증명으로 바꾸지 않는다.
   - `LOCAL_CONTROL_REGION_CODE`, `LOCAL_CONTROL_REGION_NAME`: 지역 관리기관 정보. 실제 `""`, `""`. 원본에 보존하고 필수 검색 열에서는 제외한다.

3) 1-1. 프로그램·Subpart·오염물질 필드
   - ★ PROGRAMS의 `PGM_SYS_ID`, `PROGRAM_CODE`, `PROGRAM_DESC`: 시설·프로그램·설명. 실제 `DE0000001000100090`, `CAASIP`, SIP 설명. 프로그램별 조회에 필요하다.
   - ★ PROGRAMS의 `AIR_OPERATING_STATUS_CODE/DESC`: 실제 `CLS`, `Permanently Closed`. 시설 전체 상태와 프로그램 상태를 따로 저장한다.
   - ★ PROGRAMS의 `BEGIN_DATE`, `UPDATED_DATE`: 실제 `02/22/2017`, `02/21/2020`. 원 시스템 입력·갱신 정보이며 공장 최초 가동일로 쓰지 않는다.
   - ★ PROGRAM_SUBPARTS의 `PGM_SYS_ID`, `PROGRAM_CODE`, `PROGRAM_DESC`, `AIR_PROGRAM_SUBPART_CODE`, `AIR_PROGRAM_SUBPART_DESC`: 실제 `AR0000000513900037`, `CAANESH`, Part 61 설명, `CAANESHFF`, Part 61 Subpart FF 설명. 같은 Subpart 글자라도 Part를 함께 알아야 한다.
   - ★ POLLUTANTS의 `PGM_SYS_ID`, `POLLUTANT_CODE`, `POLLUTANT_DESC`: 실제 `NH0000003300900014`, `300000322`, `TOTAL PARTICULATE MATTER`. 시설·오염물질을 연결한다.
   - ★ POLLUTANTS의 `SRS_ID`, `CHEMICAL_ABSTRACT_SERVICE_NMBR`: 실제 `1647643`, `""`. 물질 식별과 추후 다른 자료 연결에 쓴다.
   - ★ POLLUTANTS의 `AIR_POLLUTANT_CLASS_CODE/DESC`: 실제 `MIN`, `Minor Emissions`. 시설 전체 분류와 물질별 분류를 구분한다.
   - Part 63 연결은 공식 프로그램 사전을 사용한다. 예: `CAAMACT6J → Part 63 JJJJJJ`. 코드에서 `CAAMACT`만 지우면 잘못된 Subpart가 된다. [공식 Subpart 사전](https://echo.epa.gov/tools/data-downloads/icis-air-download-summary/air-program-code-subpart-descriptions)

4) 1-1. 점검·배출시험·인증 필드
   - ★ 공통 `PGM_SYS_ID`, `ACTIVITY_ID`: 시설·활동 번호. 점검 예시 `PR0000007212300011`, `121929`. 시설과 사건을 구분한다.
   - ★ `STATE_EPA_FLAG`: 담당 구분. 실제 `E` 또는 인증 예시 `S`. 기관별 이력을 구분한다.
   - ★ `ACTIVITY_TYPE_CODE/DESC`: 활동 종류. 점검 예시 `INS`, `Inspection/Evaluation`. 점검 파일에 존재한다.
   - ★ `COMP_MONITOR_TYPE_CODE/DESC`: 점검 방법. 점검 `PCE`, `PCE On-Site`; 시험 `CST`, `Stack Test`; 인증 `TVA`, `TV ACC Receipt/Review`.
   - ★ `ACTUAL_END_DATE`: 활동 날짜. 점검 `05-04-2004`, 시험 `06/24/2004`, 인증 `04/30/2015`. 원문을 보존하고 정규화한다.
   - ★ 점검 `PROGRAM_CODES`, `ACTIVITY_PURPOSE_DESC`: 실제 `""`, `Agency Priority`. 관련 규제와 점검 목적을 남긴다.
   - ★ 시험 `POLLUTANT_CODES`, `POLLUTANT_DESCS`: 실제 `HAPS [HAZARDOUS AIR POLLUTANTS/AIR TOXICS]`, `""`. 숫자만 들어간다고 가정하지 않는다.
   - ★ 시험 `AIR_STACK_TEST_STATUS_CODE/DESC`: 실제 `""`, `""`. 미확인 상태를 시험 통과로 바꾸지 않는다.
   - ★ 인증 `FACILITY_RPT_DEVIATION_FLAG`: 실제 `Y`. 인증 활동과 시설의 최종 준수 여부를 혼동하지 않기 위해 필요하다.

5) 1-1. 처분·위반 필드
   - ★ FORMAL_ACTIONS의 `PGM_SYS_ID`, `ACTIVITY_ID`, `ENF_IDENTIFIER`: 실제 `NE0000003105500410`, `600031828`, `07-2007-0086`. 시설·활동·처분 번호를 연결한다.
   - ★ `ACTIVITY_TYPE_CODE/DESC`, `STATE_EPA_FLAG`, `ENF_TYPE_CODE/DESC`: 실제 `AFR`, `Administrative - Formal`, `E`, `113A`, `CAA 113A Admin Compliance Order (Non-Penalty)`. 처분 성격을 보존한다.
   - ★ `SETTLEMENT_ENTERED_DATE`, `PENALTY_AMOUNT`: 실제 `03/08/2007`, `0`. 날짜와 신고 금액이다. 빈값과 0을 구분한다.
   - ★ INFORMAL_ACTIONS도 위 식별·종류 필드를 가진다. 실제 `ACTIVITY_ID=600027656`, `ENF_IDENTIFIER=05-200004899`, `ENF_TYPE_CODE=NOV`, 설명 `Notice of Violation`.
   - ★ 비공식 조치의 `ACHIEVED_DATE`, `OFFICIAL_FLG`: 실제 `09/27/2006`, `Y`. 공식처분 합의일과 섞지 않는다.
   - ★ VIOLATION_HISTORY의 `PGM_SYS_ID`, `ACTIVITY_ID`, `COMP_DETERMINATION_UID`: 실제 `DE0000001000100090`, `3400309508`, `DE000A0000100010009000003`. 사건 단위 식별에 필요하다.
   - ★ `AGENCY_TYPE_DESC`, `STATE_CODE`, `AIR_LCON_CODE`, `ENF_RESPONSE_POLICY_CODE`: 실제 `State`, `DE`, `""`, `HPV`. 담당 기관과 위반 분류를 보존한다.
   - ★ `PROGRAM_CODES/DESCS`, `POLLUTANT_CODES/DESCS`: 실제 `CAASIP`, SIP 설명, `300000243`, `VOLATILE ORGANIC COMPOUNDS (VOCS)`. 여러 값일 수 있다.
   - ★ `EARLIEST_FRV_DETERM_DATE`, `HPV_DAYZERO_DATE`, `HPV_RESOLVED_DATE`: 실제 `""`, `02-28-1997`, `02-19-1998`. 위반 발견·기산·해결 시점을 구분한다.
   - ★ `DSCV_PATHWAY_DATE`, `NFTC_PATHWAY_DATE`: 실제 둘 다 `""`. 원 시스템의 위반 처리 경로 날짜로 보존하며 일반 해결일로 치환하지 않는다.
   - 필드 뜻의 출처: [ICIS-Air 사전](https://echo.epa.gov/tools/data-downloads/icis-air-download-summary). 실제 헤더와 다르면 CSV를 기준으로 별칭을 기록한다.

6) 1-1. Pipeline 필드와 보조 자료
   - ★ `SOURCE_ID`, `REGISTRY_ID`, `AIR_NAME`: 실제 `PA000515538`, `110001083915`, `NORTHEAST PAVING/WASHINGTON PLANT`. CAA 시설 및 FRS 연결이다.
   - ★ `PIPELINE_FLAG`, `OFFICIAL_FLAG`, `EVAL_FLAG`, `VIOL_FLAG`, `FOUND_VIOLATION`, `EA_FLAG`, `FEA_ISSUE_DATE_FLAG`: 연결·공식 집계·점검·위반·처분 여부. 첫 행은 차례로 `N,N,N,Y,Y,N,""`이다. 식별자가 있다고 실제 사건이 존재한다고 가정하지 않는다.
   - ★ `EVAL_ACTIVITY_ID`, `EVAL_TYPE_DESC`, `EVAL_LEAD_AGENCY`, `EVAL_DATE`: 점검 연결. 실제 ID는 `-9999`, 나머지는 빈값이다. 이 ID를 실제 점검으로 만들지 않는다.
   - ★ `VIOL_ACTIVITY_ID`, `VIOL_TYPE`, `VIOL_LEAD_AGENCY`, `VIOL_PROGRAMS`: 실제 `3602684385`, `FRV`, `PA`, `CAASIP`. 위반과 제도를 연결한다.
   - ★ `VIOL_POLLUTANT_CODES/DESCS`, `VIOL_START_DATE`, `VIOL_END_DATE_DATE`, `VIOL_END_DATE`: 실제 `300000329`, `FACIL`, `06/26/2018`, `""`, `N/A`. 날짜형 종료일과 표시 문자열이 별도다.
   - ★ `EA_ACTIVITY_ID`, `EA_FEA_ACTIVITY_ID`, `EA_TYPE`, `EA_DATE`, `EA_PENALTY_AMT`: 처분 연결·종류·날짜·금액. 첫 행은 모두 빈값이다. 금액은 확인된 처분 단위로 한 번만 집계한다.
   - `SORT_ORDER`, `SORT_DATE`, `EVAL_SORT_ORDER`, `VIOL_SORT_ORDER`, `VIOL_TYPE_SORT`, `EA_SORT_ORDER`: 화면 정렬용. 실제 `55478`, `06/26/2018`, `55478`, `44050`, `1`, `55478`. 영구 사건 키로 쓰지 않고 원본에 보존한다.
   - `EA_COMP_ACTION_COST`: 실제 빈값. 공식 사전에 없는 추가 열이다. 뜻을 검증하기 전에는 벌금 집계에서 제외한다.
   - 보조 FRS는 `FRS_FACILITIES.csv`와 `FRS_PROGRAM_LINKS.csv`의 `REGISTRY_ID`, `PGM_SYS_ACRNM`, `PGM_SYS_ID`로 연결한다. 원본 표본 수집 후 실제 코드값·중복 관계를 확정한다.
   - 보조 FE&C는 `CASE_ENFORCEMENTS`, `CASE_FACILITIES`, `CASE_VIOLATIONS`, `CASE_LAW_SECTIONS`, `CASE_ENFORCEMENT_CONCLUSIONS`, `CASE_ENFORCEMENT_CONCLUSION_DOLLARS` 등을 검토한다. 사건번호·활동번호·결론번호별 범위가 다르다.
   - FE&C의 벌금·주/지방 금액·SEP 비용·준수 비용·비용 회수를 별도 필드로 보존한다. 이번에 실제 CSV 표본을 확보하지 않았으므로 상세 매핑은 보조 단계의 완료 조건으로 둔다.
   - 출처: [Pipeline 사전](https://echo.epa.gov/tools/data-downloads/caa-pipeline-download-summary), [FRS 사전](https://echo.epa.gov/tools/data-downloads/frs-download-summary), [FE&C 사전](https://echo.epa.gov/tools/data-downloads/icis-fec-download-summary).

7) 1-2. 수집 방법
   - 작업 위치: `[2] db/3) ECHO/`. 원본 ZIP과 내부 파일 명세를 `raw/{확인일}/{zip_sha256}/`에 보관한다.
   - 공식 [다운로드 목록](https://echo.epa.gov/tools/data-downloads)에서 최신 ZIP 링크를 확인한다. 핵심은 [ICIS-Air ZIP](https://echo.epa.gov/files/echodownloads/ICIS-AIR_downloads.zip)과 [CAA Pipeline ZIP](https://echo.epa.gov/files/echodownloads/pipeline_caa_downloads.zip)이다.
   - ZIP 형식·CRC·전체 바이트·필수 멤버·헤더를 검사한다. ZIP 내부 경로가 작업 폴더 밖으로 나가지 않게 검사한다.
   - FRS 연결 보완을 다음 단계에 추가하고, FE&C는 핵심 사건과 연결되는 자료부터 범위를 확정한다. 선택 자료를 핵심 11개 CSV 완료율에 섞지 않는다.
   - Exporter·Air Emissions·동결 AFS와 수질·폐기물 등 제외 자료의 판단은 전수조사 문서를 따른다.

8) 1-3. 수집 관련 유의점
   - 전체 자료는 ZIP을 이용한다. 화면 검색을 자동 반복해 전국 자료를 긁는 방식은 사용하지 않는다.
   - ZIP 생성 시각, 각 원 시스템의 기준일, 사건 발생일, 수집 시각을 따로 둔다.
   - 실제 ICIS-Air 압축 해제 크기는 838,495,852바이트였다. 메모리에 전부 올리지 않고 디스크와 스트리밍 읽기를 사용한다.
   - DB 용량은 아직 측정하지 않았다. 초기 적재 때 테이블·인덱스·임시 공간·이전 release를 합쳐 측정한 뒤 운영 용량을 정한다.

9) 1-4. 수집시 마주한 문제와 해결
   - 실제 시설 파일의 지역기관 열 이름이 사전과 달랐다. `AIR_LOCAL_CONTROL_REGION_*`와 `LOCAL_CONTROL_REGION_*`의 별칭을 버전 관리한다.
   - Pipeline에 문서화되지 않은 열이 있었다. 새 열을 삭제하지 않고 원본 보존·검토 상태로 받는다.
   - 다운로드 페이지의 표시 용량과 실제 응답 크기가 달랐다. 예상 용량을 고정하지 않고 응답·ZIP 무결성을 검사한다.

10) 1-5. 수집 결과
   - 조사용으로 ICIS-Air 10개 CSV와 Pipeline 1개 CSV의 전체 행을 읽었다. 운영 원본 보관·적재 파일 생성은 미실행이다.
   - 구현 결과에는 ZIP 기준 시각·해시·파일별 행 수·열 수·실패 여부·필터 전후 모집단을 남긴다.

11) 1-6. 수집 한계
   - EPA에 신고되지 않은 자료까지 확보할 수 없다. 자료 없음은 위반 없음도, 적용 제외도 아니다.
   - ECHO는 시설 수준이다. 개별 설비의 적용 기준·허가서 전문·모든 사건의 서술문은 이 파일들에 모두 들어 있지 않다.

## [2] Step.2 파서

1) 2-1. 파서 방법
   - ZIP 안의 CSV를 한 행씩 읽는다. 쉼표·따옴표·셀 안의 줄바꿈을 CSV 규칙대로 처리한다.
   - 파일별 헤더 매핑을 사용하고 원본 행 번호·원본값을 보존한다. 인코딩 오류를 무조건 대체문자로 덮지 않는다.
   - 모든 식별자·프로그램·우편번호는 문자열로 읽는다. 빈 문자열·`N/A`·`-9999`는 필드별 결측 규칙을 적용하고 원본값을 유지한다.
   - 날짜는 실제 관찰한 미국식 `MM/DD/YYYY`, `MM-DD-YYYY`를 명시적으로 처리한다. `05-04-2004`는 2004-05-04로 해석하며 모호한 새 형식은 보류한다.
   - 업종·프로그램·오염물질의 여러 값은 원본 구분 규칙을 확인해 자식 행으로 분리한다. 쉼표가 이름의 일부인지 먼저 확인한다.
   - `PGM_SYS_ID`로 프로그램·점검·위반을 연결한다. FRS 연결은 프로그램 종류와 번호를 함께 대조한다.
   - Part 63 후보는 CAAMACT 및 검증한 Subpart 사전으로 표시한다. NAICS 31~33은 제조업 탐색 보조값이다. 코드 미기재 시설도 별도 후보로 유지한다.
   - Pipeline의 flag와 식별자를 함께 확인한다. 가짜 연결 번호와 없는 점검·처분은 실제 사건 테이블에 만들지 않는다.
   - 벌금은 처분 단위 사실값으로 저장하고 시설·위반 연결은 따로 둔다. 사건 총액을 특정 시설이나 Part 63 위반 하나의 벌금으로 나누지 않는다.

2) 2-2. 파서 관련 유의점
   - 여러 파일의 행을 시설 번호만으로 모두 합치면 행 수가 곱해진다. 점검·위반·처분은 각자 저장하고 확인된 연결만 만든다.
   - 코드 사전에도 오래된 코드와 설명 차이가 있을 수 있다. 현재 eCFR 목차에 없는 코드는 ‘역사적/미해결’로 남긴다.
   - `BEGIN_DATE`를 공장 설립일로, `CURRENT_HPV`를 최종 준수 판정으로 바꾸지 않는다.

3) 2-3. 파서시 마주한 문제와 해결
   - 조사에서 혼합 날짜, 빈 금액, 0 금액, 숫자가 아닌 CODE, `-9999` 연결 ID를 확인했다. 필드별 변환 규칙이 필요하다.
   - 원본 모든 행의 연결키 중복률·결측률은 아직 측정하지 않았다. 운영 파서는 첫 적재에서 이 수치를 반드시 보고한다.

4) 2-4. 파서 합격 기준과 파서 실행 결과
   - 파일별 `읽은 행 = 정상 행 + 보류 행`이어야 한다. 설명 없이 사라진 행은 0개다.
   - 11개 필수 CSV와 필수 식별 필드가 있어야 한다. 새 열은 보존하고 필수 열 누락은 공개를 중단한다.
   - 선행 0, 두 날짜 형식, 셀 안 줄바꿈, 다중 코드, 0/빈 금액, `-9999`, 9906/9913 연결 번호를 검증한다.
   - 부모 없는 사건은 연결 오류로 별도 보고한다. 같은 release 안의 확정 연결에는 고아 FK가 0개여야 한다.
   - 같은 처분이 여러 시설·위반에 연결되는 표본에서 벌금 사실값이 반복 합산되지 않아야 한다.
   - 조사용 CSV 행 세기는 완료했다. 운영 정규화·관계·금액 검증 시험은 미실행이다.

5) 2-5. 파서 결과
   - 예정 산출물: 시설·프로그램·Subpart·물질·활동·위반·처분·연결 파일과 파일별 품질 보고서.
   - 포함 여부는 `national_raw`, `part63_candidate`, `manufacturing_candidate`, `unresolved` 같은 별도 분류로 기록한다. 이는 원본 필드가 아닌 설계값이다.

6) 2-6. 파서 한계
   - 구조화 이력만으로 사건의 전체 맥락이나 Part 63의 정확한 위반 조문을 알 수 없는 경우가 있다.
   - 코드·시설 이름의 유사성만으로 ECHO와 ADI 회신을 자동으로 같은 사건이라 판단하지 않는다.

## [3] Step.3 DB 적재

1) 3-1. DB 적재 방법
   - [eCFR 계획의 공통 운영 테이블](<1_eCFR 구축 계획.md>)을 사용한다. ECHO scope는 `icis_air_national`과 `caa_pipeline`의 구성 파일 명세를 포함한 하나의 공개 묶음으로 관리한다.
   - ZIP 원본 보관 → 파일별 임시 적재 → 시설·활동·관계 정규화 → 건수·금액 검사 → 현재 release 전환 순서다.
   - 전국 원본은 보존하고 DB의 조회 뷰에서 Part 63·제조업 후보를 구분한다. 필요한 경우 서비스용 뷰만 별도 색인한다.
   - 대량 행은 `COPY FROM STDIN`으로 묶어 넣는다. 오류가 난 행의 파일명과 행 번호를 기록한다.
   - ZIP들이 같은 갱신 회차에 속하는지 검사한다. 시각이 분 단위로 같아야 하는 것은 아니지만 오래된 파일이 섞이면 공개를 보류한다.

2) 3-2. DB 적재 관련 유의점
   - 임시 테이블에는 원본 문자열을 먼저 넣어, 형식 오류 하나가 전체 원본을 사라지게 하지 않도록 한다.
   - 금액은 부동소수점 대신 `numeric`을 사용한다. 통화·금액 종류·집계 단위를 함께 보존한다.
   - 현재/직전 release와 근거로 인용된 이력은 유지한다. 매주 750만 행을 무기한 복제하는 비용을 측정한 뒤, 그 밖의 이력은 보존 정책을 정한다.

3) 3-3. DB 적재 시 마주한 문제와 해결
   - 실제 DB 적재 미실행. 예상 고유키 충돌은 원본 행 보존 후 동일 행·동일 활동의 여러 속성·실제 충돌로 구분한다.
   - 시설 연결 실패는 이름만으로 합치지 않는다. 보류 목록과 FRS의 검증된 연결로 해결한다.

4) 3-4. DB 적재 실행 결과
   - 미실행. 전국 원본 행 수와 적재·보류 행 수를 대조한 뒤 Part 63 후보 수와 제조업 후보 수를 별도로 보고한다.
   - 같은 ZIP 재실행의 중복 증가 0, 벌금 중복 집계 0, 실패 시 기존 release 조회 가능을 확인해야 한다.

5) 3-5. 테이블 스키마
   - 모든 snapshot 테이블은 `release_id FK → common_dataset_release`를 가진다. 원본 근거는 `source_object_id FK → common_raw_object`, `source_file`, `source_row_no`로 되짚는다. UUID·정규화 키는 설계 필드다.
   - `echo_source_row`: `(release_id, source_file, source_row_no bigint) PK`, `raw_payload jsonb`, `row_hash text`, `parse_status text`, `source_object_id FK`. 원본의 반복 행도 추적한다.
   - `echo_facility`: `(release_id, pgm_sys_id text) PK`, `registry_id text NULL`, `name/address/city/county/state/zip/epa_region text`, `facility_type/source_class/operating_status/current_hpv text NULL`, `source_row_no bigint`. 실제 시설 ID `0100000009003E0010`, ZIP `06078`.
   - `echo_facility_identifier`: `(release_id, program_system, pgm_sys_id, registry_id) PK`, `mapping_source text`, `review_status text`. 검증된 FRS 연결을 저장한다. registry_id가 없는 행은 시설 원본에 남기고 이 테이블에 가짜 값을 만들지 않는다.
   - `echo_industry`: `(release_id, pgm_sys_id, code_system, code) PK/FK → echo_facility`, `source_locator text`. 실제 `NAICS`, `445110`. SIC·NAICS 다중값을 시설과 분리한다.
   - `echo_program`: `(release_id, pgm_sys_id, program_code) PK/FK → echo_facility`, `description/status_code/status_desc text`, `begin_date/updated_date date NULL`, `raw_dates jsonb`. 동일 키의 서로 다른 상태는 원본을 보존하고 충돌 검토한다.
   - `echo_program_subpart`: `(release_id, pgm_sys_id, program_code, subpart_code) PK/FK → echo_program`, `subpart_desc text`, `cfr_title integer NULL`, `cfr_part/cfr_subpart text NULL`, `mapping_status text`. 실제 `CAANESHFF`는 Part 61 FF, 공식 사전의 `CAAMACT6J`는 Part 63 JJJJJJ다.
   - `echo_pollutant`: `(release_id, pgm_sys_id, pollutant_key text) PK/FK → echo_facility`, `pollutant_code/description/srs_id/cas_number/class_code/class_desc text NULL`, `source_locator text`. 코드가 없으면 원본 행을 기준으로 임시 키를 만들고 `unresolved` 상태로 둔다.
   - `echo_activity`: `(release_id, activity_kind, activity_id text) PK`, `type_code/type_desc/lead_flag/monitor_code/monitor_desc text NULL`, `activity_date date NULL`, `raw_date text`, `attributes jsonb`. kind는 inspection/stack_test/titlev/formal/informal. 실제 점검 ID `121929`.
   - `echo_activity_facility`: `(release_id, activity_kind, activity_id, pgm_sys_id) PK`, 활동과 시설에 각각 복합 FK. 활동 하나와 여러 시설의 연결을 보존한다.
   - `echo_violation`: `(release_id, violation_id text) PK`, `determination_uid/policy_code/agency/state text NULL`, `first_frv_date/hpv_dayzero_date/resolved_date date NULL`, `programs/pollutants/raw_dates jsonb`. 실제 `3400309508`, `HPV`.
   - `echo_violation_facility`: `(release_id, violation_id, pgm_sys_id) PK`, 위반과 시설의 복합 FK. 여러 원본 행이 같은 위반을 설명할 때 관계와 속성을 보존한다.
   - `echo_penalty`: `(release_id, penalty_key text) PK`, `activity_kind/activity_id text`(echo_activity 복합 FK), `amount numeric NULL`, `amount_kind/currency/amount_scope text`, `raw_amount text`, `source_locator text`. 실제 공식처분 `600031828`의 `amount=0`. 액수의 출처 단위가 확인된 경우에만 사실값을 확정한다.
   - `echo_pipeline_link`: `(release_id, link_key text) PK`, `pgm_sys_id text`, `eval_activity_id/violation_activity_id/ea_activity_id/ea_fea_activity_id text NULL`(원본 ID), `flags jsonb`, `synthetic_violation boolean`, `resolution_status text`, `source_row_no bigint`. raw key 조합과 행 해시로 연결을 보존한다. 실제 활동 연결은 검증된 `resolved_eval_kind/resolved_eval_id`, `resolved_ea_kind/resolved_ea_id`를 별도 nullable 필드로 두고 각각 `(release_id, kind, id) → echo_activity` 복합 FK를 적용한다. 종류·ID가 함께 있거나 함께 NULL이어야 하며 가상 ID는 연결하지 않는다.
   - `echo_code_map`: `(dictionary_version, program_code, raw_subpart_code, raw_description) PK`, `cfr_title integer`, `cfr_part/cfr_subpart text`, `source_url text`, `review_status text`. 사전과 설명이 충돌하는 경우 하나로 단정하지 않는다.
   - FE&C 상세 스키마는 보조 파일 표본 확인 뒤 확정한다. 기본 키 축은 `ACTIVITY_ID`, `CASE_NUMBER`, `ENF_CONCLUSION_ID`이며 핵심 ICIS-Air 금액을 무조건 합쳐 더하지 않는다.
   - 인덱스: 시설 ID·FRS ID·업종 코드·프로그램/Subpart·활동 날짜·각 관계 FK. JSONB 전체를 무조건 색인하지 않고 실제 조회 열부터 선택한다.

## [4] Step.4 갱신되는 데이터 자동 적재

1) 4-1. DB 적재 방법
   - 제안 일정: 매주 월요일 05:17 UTC, 한국 14:17. 공식 갱신 완료 여부를 보고 다음 날 같은 시간 재확인한다.
   - ZIP URL·ETag/Last-Modified·실제 해시를 확인한다. 메타데이터가 없거나 신뢰할 수 없으면 파일 해시로 비교한다.
   - 새 ZIP은 전체 snapshot으로 처리한다. 사건 날짜가 오래됐어도 새로 고쳐질 수 있으므로 최근 사건만 조회하지 않는다.
   - 파일별 비교에서 새 행·내용 변경·미노출을 찾고, 모든 핵심 파일의 검사가 끝난 release만 공개한다.
   - 변화가 없으면 확인 시각만 갱신한다. 자료 변화·삭제 후보는 `common_change_log`에 기록한다.

2) 4-2. DB 적재 관련 유의점
   - 정상 전체 파일에서 빠진 행은 `not_present_in_snapshot`으로 표시한다. 이를 법적 삭제·위반 해소로 해석하지 않는다.
   - 한 파일만 실패하거나 필수 파일이 없으면 전체 새 release 공개를 보류한다.
   - 원본 ZIP 기준일·우리 마지막 성공일·공개된 release를 함께 표시한다. 매주 실행 성공이 모든 신고의 최신성을 보장하지 않는다.

3) 4-3. DB 적재 시 마주한 문제와 해결
   - 자동 적재 미실행. 예상 ZIP 손상·필수 열 누락은 원본 검사에서 차단하고 직전 정상 자료를 유지한다.
   - 재실행은 파일 해시·행 키로 동일 자료를 재사용한다. 정상 파일과 실패 파일의 진행 위치를 따로 남긴다.
   - 건수 급감·금액 급변은 비교 보고서를 만든다. 이전 대비 10% 이상 변동은 초기 검토 신호로 두되 정상 여부는 원본 설명·갱신 회차로 판단한다.

4) 4-4. DB 적재 실행 결과
   - 미실행. 동일 ZIP, 과거 사건 정정, 미노출 행, 필드 추가·삭제, ZIP 중단, 일부 파일 실패, 벌금 중복 연결을 검증한 뒤 자동화 완료로 기록한다.
   - 완료 조건: 필수 파일 11개 대조, 행 수 보존, 재실행 중복 0, 잘못된 사건 연결·금액 중복 0, 실패 및 되돌리기 후 조회 정상.
