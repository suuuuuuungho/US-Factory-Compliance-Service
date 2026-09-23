# DB 전수조사 결과

## [1] eCFR

1) 공식 제공 종류
   - 전체 제목 목록: `GET /api/versioner/v1/titles.json`.
   - 기준일별 목차: `GET /api/versioner/v1/structure/{date}/title-40.json`.
   - 기준일별 원문: `GET /api/versioner/v1/full/{date}/title-40.xml?part=63`.
   - 개정 이력 목록: `GET /api/versioner/v1/versions/title-40.json?part=63`.
   - 편집상 정정: `GET /api/admin/v1/corrections.json?title=40`. 내려받은 뒤 참조 조항이 Part 63인지 확인한다.
   - 검색 API와 화면은 탐색용이다. 전체 수집 기준은 목차와 XML이다.
   - 대체 출처: [GovInfo eCFR bulk XML](https://www.govinfo.gov/bulkdata/ECFR). 날짜와 구조를 맞춘 뒤 사용해야 하며, 현재 파일을 과거 버전으로 취급하지 않는다.
   - 출처: [eCFR 개발자 문서](https://www.ecfr.gov/developers/documentation/api/v1), [개발자 자료](https://www.ecfr.gov/reader-aids/ecfr-developer-resources).

2) 직접 센 현재 자료
   - 제목 목록: 50개. 이 중 예약된 제목도 있어 50개 모두에 본문이 있는 것은 아니다.
   - Title 40: `Protection of Environment`.
   - `up_to_date_as_of=2026-09-10`, `latest_amended_on=2026-09-09`, `latest_issue_date=2026-09-09`, `import_in_progress=false`.
   - Part 63 목차: 하위 묶음 `subpart` 158개, 조문 `section` 2,473개, 부록 종류 `appendix` 647개, 중간 제목 `subject_group` 492개.
   - 예약 표시: subpart 19개, section 88개, appendix 2개. 예약 묶음은 범위 이름을 가진 한 노드일 수도 있다.
   - 따라서 내용 있는 subpart 노드는 139개다. 158을 실제 업종 수로 부르면 안 된다.
   - 전체 XML: 26,332,596바이트. 목차와 XML의 subpart·section·appendix·subject group 개수가 일치했다.
   - XML 태그: `P` 63,893개, `TABLE` 784개, `img` 1,511개, `MATH` 482개. 이미지 수는 태그 수이며 서로 다른 이미지 파일 수가 아니다.
   - 출처: [제목 응답](https://www.ecfr.gov/api/versioner/v1/titles.json), [기준일 목차](https://www.ecfr.gov/api/versioner/v1/structure/2026-09-10/title-40.json), [Part 63 XML](https://www.ecfr.gov/api/versioner/v1/full/2026-09-10/title-40.xml?part=63).

3) 하위 묶음 전체 식별자
   - 한 글자: `A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z`.
   - 두 글자 및 예약 범위: `AA, BB, CC, DD, EE, FF, GG, HH, II, JJ, KK, LL, MM, NN, OO, PP, QQ, RR, SS, TT, UU, VV, WW, XX, YY, ZZ-BBB`.
   - 세 글자: `CCC, DDD, EEE, FFF, GGG, HHH, III, JJJ, KKK, LLL, MMM, NNN, OOO, PPP, QQQ, RRR, SSS, TTT, UUU, VVV, WWW, XXX`.
   - 네 글자: `AAAA, BBBB, CCCC, DDDD, EEEE, FFFF, GGGG, HHHH, IIII, JJJJ, KKKK, MMMM, NNNN, OOOO, PPPP, QQQQ, RRRR, SSSS, TTTT, UUUU, VVVV, WWWW, XXXX, YYYY, ZZZZ`.
   - 다섯 글자: `AAAAA, BBBBB, CCCCC, DDDDD, EEEEE, FFFFF, GGGGG, HHHHH, IIIII, JJJJJ, KKKKK, LLLLL, MMMMM, NNNNN, OOOOO, PPPPP, QQQQQ, RRRRR, SSSSS, TTTTT, UUUUU, VVVVV, WWWWW, XXXXX, YYYYY, ZZZZZ`.
   - 여섯 글자: `AAAAAA, BBBBBB, CCCCCC, DDDDDD, EEEEEE, FFFFFF, GGGGGG, HHHHHH, IIIIII, JJJJJJ, KKKKKK, LLLLLL, MMMMMM, NNNNNN, OOOOOO, PPPPPP, QQQQQQ, RRRRRR, SSSSSS, TTTTTT, UUUUUU, VVVVVV, WWWWWW, XXXXXX, YYYYYY, ZZZZZZ`.
   - 일곱 글자 및 예약 묶음: `AAAAAAA, BBBBBBB, CCCCCCC, DDDDDDD, EEEEEEE, FFFFFFF and GGGGGGG, HHHHHHH`.
   - 예약 노드: `K, P, V, Z, FF, ZZ-BBB, FFF, KKK, SSS, WWW, BBBB, OOOOO, VVVVV, XXXXX, AAAAAA, IIIIII, KKKKKK, UUUUUU, FFFFFFF and GGGGGGG`.
   - 식별자를 알파벳으로 만들어 채우지 않는다. 실제 목차에 없는 `LLLL` 같은 값을 생성하면 잘못된 자료가 생긴다.

4) 원본 구조와 실제 값
   - 목차 `identifier`: 항목 번호. 예: `63`, `A`, `63.1`.
   - `type`: 항목 종류. 예: `part`, `subpart`, `section`, `appendix`, `subject_group`.
   - `label`, `label_level`, `label_description`: 전체 제목·짧은 제목·설명. 예: `Subpart A—General Provisions`.
   - `children`: 하위 항목 배열. `reserved`: 예약 여부. `volumes`: 인쇄본 권 번호. 예: Part 63의 `[11,12,13,14,15,16]`에 해당하는 문자열 배열.
   - `size`, `descendant_range`, `received_on`: 제공 크기·하위 범위·수신 시각. 예: `63.1 – 63.12099`, `2024-06-04T19:10:31-0400`. `size`는 이번 XML의 실제 바이트 수와 같지 않았다.
   - XML: `DIV5 TYPE=PART`, `DIV6 TYPE=SUBPART`, `DIV7 TYPE=SUBJGRP`, `DIV8 TYPE=SECTION`, `DIV9 TYPE=APPENDIX`.
   - 조문 예: `DIV8 N="63.1"`, `HEAD=§ 63.1 Applicability.`, 첫 문단 시작은 `(a) General. (1)`.
   - 본문은 `P` 외에도 표·각주·수식·이미지·출처·편집자 주가 있다. `P`만 추출하면 누락된다.
   - 목차에서 `Table 1 to Subpart A of Part 63`도 `appendix`로 분류된다. 647개를 모두 이름이 Appendix인 부록으로 해석하면 안 된다.

5) 이력과 날짜
   - 이력 API의 8페이지를 모두 읽어 7,387개를 확인했다. 앞 7페이지 각 1,000개, 마지막 387개이며 동일한 전체 행의 중복은 없었다.
   - 이력 종류: section 4,709개, appendix 2,678개. `substantive=true` 5,557개, `false` 1,830개, `removed=true` 25개. 이 항목들은 서로 다른 분류이므로 모두 더하지 않는다.
   - `issue_date` 범위는 2017-01-01~2026-07-06이었다. 각 과거 버전의 본문은 아직 전수 다운로드하지 않았다.
   - 페이지는 `?part=63&page=2`처럼 조회했다. `per_page=1000`까지 명시한 요청은 HTTP 400이었다. 응답에 나온 필드가 모두 입력 매개변수인 것은 아니다.
   - 원본 필드: `date`, `amendment_date`, `issue_date`, `identifier`, `name`, `part`, `subpart`, `title`, `type`, `substantive`, `removed`.
   - Title 40 정정 목록은 640개 응답했다. 이는 Part 63 정정 640개라는 뜻이 아니다.
   - `latest_amended_on`은 실질 변경, `latest_issue_date`는 비실질 변경까지 포함한 발행 기준, `up_to_date_as_of`는 어디까지 반영됐는지를 나타낸다. 셋을 하나의 갱신일로 합치지 않는다. [날짜 설명](https://www.ecfr.gov/reader-aids/ecfr-developer-resources/understanding-ecfr-dates)

6) 실제 문제와 확인된 해결
   - 전체 XML 요청이 HTTP 406을 반환했다. 오류 본문은 응답 압축 허용 헤더를 요구했다.
   - `Accept-Encoding: gzip`을 보내고 응답 압축을 풀자 HTTP 200으로 전체 XML을 읽었다.
   - 일부 개발자 웹페이지는 접근 확인 화면으로 이동했다. API 성공 여부와 설명 화면 성공 여부를 별도로 검사해야 한다.
   - XML의 `hierarchy_metadata.path`에 `_SUBSTITUTE_DATE_`가 있었다. 이 문자열을 그대로 사용자 링크로 쓰지 말고 검증한 기준일을 넣는다.
   - 원문 SHA-256: `f381f62280ce8f60d60e28bc9d192155d051e575502e78f6e48f869f180de13c`.

## [3] Federal Register

1) 제공 범위와 수집 출처
   - API 목록·상세 JSON, 본문 XML·HTML·텍스트, 공식 PDF, Public Inspection 사전 공개본이 있다.
   - API는 키 없이 공개된다. 온라인 API 범위는 1994년 이후 자료를 기본으로 삼는다. 오래된 자료는 본문 형식의 제공 여부를 개별 확인한다.
   - 이번 전수 목록 조건: `conditions[cfr][title]=40`, `conditions[cfr][part]=63`, `order=oldest`, `per_page=1000`.
   - 첫 주소: [Part 63 목록](https://www.federalregister.gov/api/v1/documents.json?per_page=1000&conditions%5Bcfr%5D%5Btitle%5D=40&conditions%5Bcfr%5D%5Bpart%5D=63&order=oldest). 이어지는 `next_page_url`을 그대로 따라갔다.
   - 공식 문서: [API](https://www.federalregister.gov/developers/documentation/api/v1), [개발자 자료](https://www.federalregister.gov/reader-aids/developer-resources), [GovInfo bulk FR](https://www.govinfo.gov/bulkdata/FR).

2) 직접 확인한 전체 목록
   - 표시 건수 1,532건. 1페이지 1,000행, 2페이지 532행, 다음 페이지 없음.
   - 문서번호만 세면 1,531개다. 이유는 `03-5521`이 `2003-05-27` Rule과 `2003-08-28` Correction에 함께 쓰였기 때문이다.
   - 이 두 행은 제목은 같지만 날짜와 URL이 다르다. 한 행을 버리는 단순 중복 제거는 잘못이다.
   - 목록 기준 종류: Rule 733행, Proposed Rule 720행, Correction 28행, Uncategorized Document 51행.
   - 목록 날짜 범위: 1994-01-11부터 2026-07-06까지. 이것은 이 검색 응답의 범위이며 이후 관련 문서가 절대 없다는 보장은 아니다.
   - 설계 결정: 원본 `html_url`을 보존하고 `(publication_date, document_number)`를 기본 식별 조합으로 쓴다. 충돌 때 URL·PDF·공식 서지정보를 대조한다.

3) 실제 상세 응답 예시
   - [2026-03638 상세 JSON](https://www.federalregister.gov/api/v1/documents/2026-03638.json)을 확인했다.
   - `document_number=2026-03638`, `type=Rule`, `action=Final rule.`.
   - `publication_date=2026-02-24`, `effective_on=2026-04-27`, `citation=91 FR 9088`, `volume=91`, `start_page=9088`, `end_page=9134`.
   - `cfr_references=[{title:40, part:"63", chapter:null, citation_url:null}]`.
   - `docket_ids`에 `EPA-HQ-OAR-2018-0794`, `regulation_id_numbers`에 `2060-AW68`이 있다.
   - `dates`에는 시행일 외의 날짜 설명도 들어간다. 단일 시행일 필드만으로 모든 적용 기한을 설명할 수 없다.
   - `correction_of=null`, `corrections=[]`가 실제 존재한다. 연결 필드가 비어 있어도 관련 정정문이 없는 것으로 단정하지 않는다.

4) 전체 필드 종류
   - 식별·제목: `document_number`, `title`, `type`, `subtype`, `action`, `abstract`, `agencies`.
   - 날짜·상태: `publication_date`, `effective_on`, `comments_close_on`, `signing_date`, `dates`, `significant`, `not_received_for_publication`, `disposition_notes`.
   - 규정·관계: `cfr_references`, `correction_of`, `corrections`, `docket_ids`, `dockets`, `regulation_id_numbers`, `regulation_id_number_info`.
   - 원문·근거: `html_url`, `json_url`, `pdf_url`, `public_inspection_pdf_url`, `full_text_xml_url`, `body_html_url`, `raw_text_url`, `mods_url`, `images`, `images_metadata`.
   - 서지·분류: `citation`, `volume`, `start_page`, `end_page`, `page_length`, `topics`, `toc_doc`, `toc_subject`.
   - 의견수렴: `comment_url`, `regulations_dot_gov_info`, `regulations_dot_gov_url`.
   - 기타: `executive_order_notes`, `executive_order_number`, `presidential_document_number`, `proclamation_number`, `page_views`.
   - 상세 응답의 모든 원본 필드는 보존한다. 검색용 정규 필드의 선택과 설명은 [FR 구축 계획](<../db 구축 계획/2_Federal Register 구축 계획.md>)에 적었다.

5) 한계와 설계 결정
   - `cfr_references`는 대개 Part 수준이다. 본문에서 Subpart·section을 찾고, 원문 위치와 추출 신뢰도를 함께 저장해야 한다.
   - 목록에 Notice가 0건이라고 관련 Notice가 없다는 뜻은 아니다. Part 메타데이터가 빠진 공고·연장·철회는 본문 검색, docket/RIN, 조문 출처로 보완한다.
   - Proposed Rule과 Public Inspection은 현재 시행 규정으로 표시하지 않는다. 확정 규칙도 발행일과 시행일을 구분한다.
   - FederalRegister.gov의 XML 표시본과 법적 공식본은 구분된다. 근거 확인용 GovInfo PDF 링크를 보존한다. [공식 상태 안내가 포함된 API 페이지](https://www.federalregister.gov/developers/documentation/api/v1)
   - 전체 1,532행의 본문·첨부 다운로드, 모든 보완 검색의 전수 수집은 미실행이다.
   - 목록 응답 SHA-256: 1페이지 `95465dc8d4f5520d2beb59c44c94dfa510774461df9ddb205f3ccbf294581ae2`, 2페이지 `53c32f7f13443b8eba19e4c50a187009cc78caeee58803e411e4035333eb039c`.

## [4] ECHO

1) 공식 제공 자료의 포함·제외 판단
   - 핵심: `ICIS-Air`의 시설·프로그램·Subpart·오염물질·점검·배출시험·Title V 인증·공식처분·비공식처분·위반 이력, 그리고 `CAA Pipeline`의 사건 연결.
   - 보조: `FRS Facilities and Linkages`는 시설 식별자 연결, `ICIS FE&C`는 연방 집행사건의 상세 설명과 금액 검증에 필요하다.
   - 선택: `ECHO Exporter`는 시설별 요약 확인용이다. 개별 사건 원본을 대신하지 않는다. `Air Emissions`는 NEI·GHGRP·TRI·Clean Air Markets 배출량을 보완하지만 보고연도가 다르다.
   - 과거 자료: `AFS`는 2014-10-17 기준 동결 자료다. ICIS-Air와 함께 매주 새 자료인 것처럼 적재하지 않는다.
   - 현재 서비스에서 제외: 수질 ICIS-NPDES·DMR·허용기준·MSGP·하수월류·바이오솔리드·WQI, 폐기물 RCRAInfo·RCRA Pipeline, 식수 SDWA, 인구·부족지역 공간자료, 별도 PFAS 다운로드. 필요해질 때 범위를 추가한다.
   - 출처: [전체 다운로드 목록](https://echo.epa.gov/tools/data-downloads), [FRS 사전](https://echo.epa.gov/tools/data-downloads/frs-download-summary), [FE&C 사전](https://echo.epa.gov/tools/data-downloads/icis-fec-download-summary).

2) 직접 읽은 ICIS-Air 전체 CSV
   - 파일: [ICIS-AIR_downloads.zip](https://echo.epa.gov/files/echodownloads/ICIS-AIR_downloads.zip).
   - 응답 크기 70,168,265바이트. HTTP `Last-Modified=2026-09-13 02:10:24 GMT`.
   - `ICIS-AIR_FACILITIES.csv`: 280,071행, 19필드. 시설 기본 정보.
   - `ICIS-AIR_PROGRAMS.csv`: 458,110행, 7필드. 시설별 규제 프로그램.
   - `ICIS-AIR_PROGRAM_SUBPARTS.csv`: 191,226행, 5필드. 시설별 하위 규정 코드.
   - `ICIS-AIR_POLLUTANTS.csv`: 977,624행, 7필드. 시설별 오염물질.
   - `ICIS-AIR_FCES_PCES.csv`: 1,819,117행, 10필드. 전체·부분 점검.
   - `ICIS-AIR_STACK_TESTS.csv`: 655,094행, 10필드. 굴뚝 배출시험.
   - `ICIS-AIR_TITLEV_CERTS.csv`: 2,583,180행, 7필드. Title V 준수 인증 활동.
   - `ICIS-AIR_FORMAL_ACTIONS.csv`: 106,520행, 10필드. 공식 처분과 금액.
   - `ICIS-AIR_INFORMAL_ACTIONS.csv`: 339,879행, 10필드. 경고 등 비공식 조치.
   - `ICIS-AIR_VIOLATION_HISTORY.csv`: 102,676행, 16필드. HPV·FRV 위반 이력.
   - 합계 7,513,497행. CSV 헤더 제외, CSV 파서 기준이며 중복 제거 전 행 수다. 시설 수나 사건 수를 합산한 값은 아니다.
   - 각 파일의 모든 행을 읽고 헤더와 첫 행을 확인했다. 전체 행의 법적 내용·연결키 품질까지 검증한 것은 아니다.
   - SHA-256: `253697f44fbb84cf252ea2bcdca4d52a806b0798b57dc4e3fc41e0f08c111005`.

3) CAA Pipeline 직접 확인
   - 파일: [pipeline_caa_downloads.zip](https://echo.epa.gov/files/echodownloads/pipeline_caa_downloads.zip).
   - 응답 크기 5,332,282바이트. HTTP `Last-Modified=2026-09-13 06:12:06 GMT`.
   - 구성: `PIPELINE_CAA_00_COMPLETE.csv` 한 개, 67,123행, 35필드.
   - 점검 `EVAL_ACTIVITY_ID`, 위반 `VIOL_ACTIVITY_ID`, 처분 `EA_ACTIVITY_ID`·`EA_FEA_ACTIVITY_ID`가 한 행에서 연결된다.
   - 같은 처분이 여러 연결 행에 나타날 수 있다. `EA_PENALTY_AMT`를 행마다 더하면 벌금이 부풀 수 있다.
   - SHA-256: `75e018acd8dabf485077e9f220d37f5bd55607d830ff32bb92257a7b793f38fa`.
   - 출처: [Pipeline 필드 설명](https://echo.epa.gov/tools/data-downloads/caa-pipeline-download-summary).

4) 실제 값과 발견한 차이
   - 시설 첫 행: `PGM_SYS_ID=0100000009003E0010`, `REGISTRY_ID=110070834547`, `FACILITY_NAME=HIGHLAND PARK MARKET`, `STATE=CT`, `ZIP_CODE=06078`, `NAICS_CODES=445110`.
   - 이 예시는 원본 모양 확인용이다. 제조업 시설이라고 골라낸 표본은 아니다.
   - 공식 사전은 `AIR_LOCAL_CONTROL_REGION_CODE/NAME`, 실제 CSV는 `LOCAL_CONTROL_REGION_CODE/NAME`이다. 원본 헤더를 보존하고 별칭으로 처리해야 한다.
   - 점검 첫 행은 `ACTIVITY_ID=121929`, `ACTUAL_END_DATE=05-04-2004`; 배출시험 첫 행은 `ACTUAL_END_DATE=06/24/2004`. 날짜 구분자가 섞여 있다.
   - 공식처분 첫 행: `ACTIVITY_ID=600031828`, `ENF_IDENTIFIER=07-2007-0086`, `ENF_TYPE_CODE=113A`, `PENALTY_AMOUNT=0`. 0과 빈칸은 다르다.
   - Pipeline 첫 행: `SOURCE_ID=PA000515538`, `EVAL_ACTIVITY_ID=-9999`, `FOUND_VIOLATION=Y`, `VIOL_ACTIVITY_ID=3602684385`, `EA_PENALTY_AMT=""`.
   - Pipeline의 실제 마지막 필드 `EA_COMP_ACTION_COST`는 위 공식 설명 목록에 없었다. 원본으로 보존하고 벌금과 합치지 않는다.
   - 공식 설명상 `VIOL_ACTIVITY_ID`가 `9906`·`9913`으로 시작하면 화면 연결용으로 만든 번호일 수 있다. 이를 실제 위반 하나로 세지 않는다.
   - 배출시험의 `POLLUTANT_CODES`에 숫자 대신 `HAPS [HAZARDOUS AIR POLLUTANTS/AIR TOXICS]`가 있었다. 이름이 CODE라고 숫자로 강제 변환하지 않는다.

5) 갱신과 한계
   - 대용량은 공식 ZIP을 이용한다. 화면 검색 결과의 수 제한을 전체 시설 수로 오해하지 않는다. [서비스 안내](https://echo.epa.gov/tools/web-services)
   - 주간 갱신 대상이라도 ZIP과 원 시스템의 시각은 다르다. ECHO 자료는 원 시스템의 특정 시점 사본이다.
   - 신고 지연과 소규모 시설의 자료 누락이 있다. 검색되지 않음·위반 없음·미신고·적용 제외는 서로 다른 상태다. [자료 갱신·완전성 안내](https://echo.epa.gov/resources/echo-data/about-the-data)
   - 시설 단위 자료만으로 설비별 Part 63 적용을 판정할 수 없다. 프로그램·Subpart 기록은 후보 탐색에 사용한다.
   - FRS ID와 CAA 시설 ID는 다르다. 선행 0을 보존하는 문자열로 저장하고 일대다 연결을 허용한다.
   - 설명 파일의 ‘80만 개 이상’을 고정 건수로 쓰지 않는다. 공식 Exporter 설명은 150만 개 이상을 안내하지만, 이번 ICIS-Air 280,071행과는 모집단이 다르다.
   - FRS·Exporter·FE&C·Air Emissions 원본의 전체 행 수와 저장 비용은 이번에 측정하지 않았다. 핵심 11개 CSV의 범위와 구분한다.

## [5] ADI와 CAA 적용·준수 Dashboard

1) 두 저장소의 범위
   - EPA의 현재 안내는 ADI를 2019년 5월 이전, Dashboard를 그 이후 서명된 회신으로 구분한다.
   - ADI는 목록·요약·참조·텍스트 다운로드와 회신 파일을, Dashboard는 표 형태의 목록과 PDF 링크를 제공한다. 실제 ADI의 M200005 원문 링크도 PDF를 반환했다.
   - CAA §111·§112·§129는 법률 조문 번호이고 CFR Part 60·61·63은 규정집 번호다. `112=Part 63` 같은 단순 숫자 변환은 하지 않는다.
   - 2019년 5월 경계는 날짜로 강제 분할해 누락시키지 않는다. 두 원본 목록을 각각 확인하고 중복 관계를 기록한다.
   - 출처: [EPA 통합 안내](https://www.epa.gov/complying-air-emissions-standards-stationary-sources), [ADI](https://cfpub.epa.gov/adi/), [Dashboard](https://www.epa.gov/complying-air-emissions-standards-stationary-sources/epa-determinations-compliance-and).

2) ADI의 확인된 화면·필드
   - 검색 조건: 문서번호, 최근 추가분, 분류, EPA 사무소, 날짜 범위, 작성자, 단어, Subpart, 규정 인용.
   - 실제 분류 선택지: `Asbestos`, `CFC`, `Federal Plan`, `GACT`, `MACT`, `NESHAP`, `NSPS`, `Woodstoves`.
   - 따라서 `MACT` 하나만 고르면 Part 63의 GACT 관련 자료를 놓칠 수 있다. 전체 목록에서 Part·Subpart·본문 인용을 함께 확인해야 한다.
   - 원본 문서 필드: `Control Number`, `Category`, `EPA Office`, `Date`, `Title`, `Recipient`, `Author`, `Subparts`, `References`, `Abstract`, `Letter`.
   - 실제 검색 폼에는 Subpart 선택지 256개, Reference 선택지 2,819개가 있었다. 각각 `All` 선택지를 포함한 값이며 문서 건수가 아니다.
   - 최근 추가분 선택지의 최신 표시는 `October 22, 2020`이었다. 이것은 회신 서명일도, 서비스 전체의 최신 규정일도 아니다.
   - 공식 가이드는 100건씩 페이지 이동하고 페이지별 선택 문서를 `.adi` 텍스트로 다운로드하는 방법을 설명한다. [ADI 사용 가이드](https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_users_guide)

3) ADI 전수 목록 확인 상태
   - 공개 검색 폼 → 전체 조건 검토 → 결과 화면을 직접 조회했다. 결과의 `results_length=3825`, HTML의 문서 선택 항목 3,825개, 고유 Control Number 3,825개가 일치했다.
   - 현재 결과 HTML에는 전체 3,825개가 포함되어 있었다. 오래된 가이드의 100개 페이지 설명과 다르므로 실제 전체 행과 화면의 페이지 표시를 대조해야 한다.
   - 실제 결과에 `M200005`, 제목 `Applicability Determination for a Lithium Ion Battery Manufacturing Facility`, `Letter Date=04/08/2020`, `Categories=MACT, NESHAP`, `Office=Region 5`, `Letter Author=Sara Breneman`이 있었다.
   - [M200005 원문](https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id=M200005)은 HTTP 200, `application/pdf`, 207,639바이트였다. PDF 내용 전체의 파싱·검토는 미실행이다.
   - 공식 소개의 ‘2019년 5월 이전’과 실제 ADI의 2020년 회신이 충돌한다. 실제 목록을 기준으로 모두 보존하고 날짜 경계로 잘라 버리지 않는다.
   - `ZB053`, `ZB054`의 목록 날짜는 `12/30/1899`였다. 오래된 시스템의 비정상 기본값일 가능성이 있으나 원인은 확인하지 못했다. 원본 날짜를 보존하고 정상 서명일로 바로 채택하지 않는다.
   - 3,825개는 ADI 전체 목록 수다. Part 63 최종 관련 문서 수는 전체 상세 메타데이터·본문을 확인한 뒤 별도로 확정해야 한다.
   - 공식 가이드에 있는 ‘분기별 추가’를 현재도 보장되는 갱신 약속으로 쓰지 않는다. 최신 EPA 안내와 실제 목록 변경을 기준으로 관리한다.

4) Dashboard 전체 목록 직접 확인
   - HTML 전체 표: 236행, 회신 링크 236개. 초기 화면의 50개 표시가 전체 건수가 아니었다.
   - `Affected Subpart`에 Part 63이 명시된 행: 132행, 연결 링크 132개, 서로 다른 Part 63 Subpart 코드 37개.
   - 해당 코드는 `A, AAAA, AAAAA, BB, CC, CCC, CCCCCC, DDDD, DDDDD, EEE, EEEE, F, FFFF, FFFFFF, G, HH, HHHHHH, HHHHHHH, JJJ, JJJJJJ, LLL, LLLLL, M, MM, MMMM, O, PPPP, PPPPPP, RRR, RRRRR, S, SS, UUU, UUUUU, XXXXXX, YYYY, ZZZZ`다.
   - 132는 Part 63 명시 행 수다. PDF 내용까지 확인한 최종 관련 문서 수나 중복 제거한 판정 수는 아니다.
   - 원본 열은 네 개: `Facility Name`, `Title`, `Affected Subpart`, `Link to Responses`.
   - 실제 예: `King Systems Corporation`, `Part 63, PPPP`, 링크 표시 날짜 `2020-06-16`.
   - 실제 PDF: [King Systems 회신](https://www.epa.gov/system/files/documents/2022-05/King%20Systems%20Corp%20Response_6-16-20.pdf).
   - 페이지의 표시 갱신일은 `September 19, 2025`다. 조사일과 다르며, 현재까지 모든 EPA 회신을 수록했다는 뜻도 아니다.

5) 발견한 문제와 설계 영향
   - 회신 링크 대부분이 Outlook Safe Links로 감싸져 있다. 실제 `url` 매개변수에서 EPA PDF 주소를 읽고 원래 링크도 함께 보존한다.
   - 링크 표시가 항상 날짜는 아니다. 첫 행에는 PDF 파일명이 표시된다. 서명일은 PDF 본문 확인을 우선하고 목록 표시·파일명 날짜와 구분한다.
   - `Westvaco Facility`의 목록은 Part 63 AAAAA인데 파일명에는 `40-cfr-60-subpart-aaaaa`가 들어 있다. 파일명만으로 규정 번호를 결정하지 않는다.
   - 한 행에 여러 Part·Subpart가 있다. 한 문서와 여러 규정의 연결을 각각 저장한다.
   - 스캔·재입력 문서에 오류가 있을 수 있다는 공식 안내가 있다. 텍스트가 짧거나 비어 있으면 OCR과 원문 확인이 필요하다.
   - 특정 시설에 대한 허용·면제·기한 연장은 모든 공장에 통하는 규칙으로 바꾸지 않는다.

## [6] 구축에 반영할 공통 결정

1) 보존과 연결
   - 원본 파일, 출처 URL, 읽은 시각, 원본 기준일, SHA-256을 묶어 보존한다.
   - 원본이 바뀌면 이전 근거를 덮어쓰지 않고 새 버전을 만든다. 규정의 법적 적용 기간과 우리가 관찰한 기간을 구분한다.
   - 규정 연결은 `title + part + subpart + section`을 사용한다. 시설 연결은 EPA 식별자를 우선한다. 시설 이름만 같은 자료를 자동으로 합치지 않는다.
   - 파서의 추출값·추정 연결은 원본 값과 별도 표시한다. 연결에 실패해도 원문이 사라지지 않게 보류 목록에 남긴다.

2) 갱신 방향
   - eCFR·FR: 매일 확인하는 계획. 개정·정정·시행일 변경을 각각 다룬다.
   - ECHO: 공식 ZIP의 주간 새 버전을 확인하는 계획. 사건 발생일 이후 자료만 가져오는 방식은 과거 정정을 놓친다.
   - ADI: 월간 목록 재대조 계획. Dashboard: 주간 목록 재대조 계획. 이 주기는 우리 운영안이며 EPA의 보장 주기가 아니다.
   - 수집·파싱·검사·적재가 모두 끝난 묶음만 서비스에 공개한다. 실패하면 직전 정상 자료를 유지하고, 마지막 성공일을 표시한다.

3) 실제 구축 순서
   - 공통 실행 기록과 원본 보관 → eCFR → Federal Register → ECHO 핵심 자료 → ADI + Dashboard → 예약 실행·복구 검증.
   - PostgreSQL을 기준으로 한 설계안이다. 실제 DB 서버·저장소·용량·실행 환경은 아직 확인하지 않았다.
   - 스케줄러는 한 곳에서만 실행한다. 예약 작업 정의는 구현 단계에 만들며 이번에 외부 시스템을 변경하지 않았다.

4) 후속 문서
   - [eCFR 구축 계획](<../db 구축 계획/1_eCFR 구축 계획.md>)
   - [Federal Register 구축 계획](<../db 구축 계획/2_Federal Register 구축 계획.md>)
   - [ECHO 구축 계획](<../db 구축 계획/3_ECHO 구축 계획.md>)
   - [ADI + CAA 구축 계획](<../db 구축 계획/4_ADI+CAA 구축 계획.md>)

## [7] 출처와 재확인 방법

1) 1차 출처
   - NARA/OFR·GPO: 위 eCFR 제목·목차·전체 XML·이력·정정 API와 날짜 설명.
   - NARA/OFR·GPO: 위 Federal Register 목록·상세 API, GovInfo 원문·bulk 자료.
   - EPA: 위 ECHO 다운로드 ZIP·필드 사전·갱신 안내.
   - EPA: 위 ADI 검색·가이드, CAA 적용·준수 Dashboard와 회신 링크.
   - 모두 2026-09-14 확인. 원본이 별도로 표시한 기준일·갱신일은 각 절에 적었다.

2) 다시 셀 때의 규칙
   - eCFR는 같은 기준일의 목차와 XML을 비교한다. 태그 수·예약 노드·실제 문서 수를 섞지 않는다.
   - FR은 `next_page_url`이 없을 때까지 수집하고 문서번호와 발행일을 함께 대조한다.
   - ECHO는 ZIP별 해시와 내부 파일명을 기록하고 CSV 파서로 헤더를 제외한 행 수를 센다.
   - ADI는 전체 검색의 총건수와 모든 페이지의 Control Number를 대조한다. Dashboard는 HTML 전체 행·Part 63 명시 행·PDF 성공 건수를 따로 센다.
   - API나 원본 파일의 내용이 바뀌면 이번 수치를 합격 기준으로 고정하지 않고 새 원본의 전체 건수와 대조한다.
