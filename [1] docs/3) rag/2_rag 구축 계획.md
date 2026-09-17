# RAG 구축 계획

이 문서는 [DB 구축 계획](<../2) db/db 구축 계획/1_eCFR 구축 계획.md>)이 만든 자료를 "찾아주는" 계획이다. 

설계 원칙은 [Anthropic Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)을 따르고, 

임베딩은 법률 특화 모델 [Kanon 2 Embedder](https://isaacus.com/blog/introducing-kanon-2-embedder)를 쓴다. 

지금은 **v1(설계)**이다. 데이터가 아직 적재되지 않았으므로 실측이 필요한 숫자는 `실측 후 기입`으로 표시했고, 

eCFR 적재 후 v2에서 채운다. 운영 색인·검색·평가는 모두 미실행이다.

## [0] 이 문서를 지금 쓰는 이유와 두 번에 나눠 쓰는 방법

1) 지금(적재 전) 정하는 것
   - 청크(검색 조각) 단위, 청크가 반드시 들고 있어야 할 정보, 벡터 크기, 갱신 연결 방법.
   - 이 네 가지는 DB 파서와 테이블 모양을 바꾼다. 나중에 정하면 eCFR을 다시 파싱·적재해야 한다.

2) eCFR 적재 후(v2) 채우는 것
   - 조문별 토큰 분포, 컨텍스트 생성·임베딩 실제 비용, 평가셋 실측 실패율, top-k, 리랭커 효과.
   - 네 데이터셋을 다 기다리지 않는다. eCFR 하나만 들어오면 실측할 수 있다.

3) 순서
   - v1 설계(이 문서) → eCFR 적재 → 실측·평가 → v2 갱신 → Federal Register·ADI/Dashboard 확장.

## [1] 무엇을 찾아주는 검색인가

1) 질문의 모양
   - 사용자는 공장 실무자다. 공정, 원료, 설비, 배출 물질, 규모 같은 "현장 말"로 묻는다.
   - 예: "알루미늄 다이캐스팅에 도장 라인이 있고 용제를 연 12톤 쓴다. 어떤 Part 63 Subpart를 봐야 하나?"
   - 검색 언어는 영어다. 규정 원문과 Kanon 2가 영어 기준이기 때문이다. 한국어 입력을 받는다면 임베딩 전에 영어로 바꾸는 단계를 둔다. 그 단계의 위치는 `미정`이다.

2) 무엇을 돌려주나
   - 적용 가능성이 있는 Subpart·조문 후보와, 그 후보의 적용 여부를 가르는 판정 기준 조문.
   - 모든 결과는 인용 위치(`40 CFR 63.xxxx(a)`), 기준일(release), 원문 링크를 갖는다. 인용 없는 결과는 내보내지 않는다.
   - 최종 적용 판정은 하지 않는다. [프로젝트 정의](<../1) project/1_project.md>)와 같다.

3) 검색 대상과 순서
   - eCFR: 1순위. 후보 조항과 판정 기준의 근거 원문이다. 벡터+키워드 검색 대상이다.
   - Federal Register: 찾은 조문이 최근 바뀌었는지, 시행 전인지 붙여준다. 벡터+키워드 검색 대상이다.
   - ADI + CAA Dashboard: 비슷한 공장에 EPA가 뭐라고 답했는지 선례를 붙여준다. 벡터+키워드 검색 대상이다.
   - ECHO: 벡터 검색을 하지 않는다. 시설·Subpart 코드·업종 코드로 SQL 조회해서 결과에 덧붙인다.

4) 왜 RAG를 건너뛸 수 없나
   - Anthropic 기준으로 코퍼스가 20만 토큰(약 500쪽) 이하면 RAG 없이 프롬프트에 통째로 넣고 캐싱하라고 한다.
   - Part 63은 XML만 26,332,596바이트, 조문 2,473개, 표 784개다. 20만 토큰을 훨씬 넘는다. 본문 토큰 수는 `실측 후 기입`.

## [2] 설계 원칙 — Contextual Retrieval

1) 핵심 생각
   - 조문을 잘게 자르면 "이 조각이 어느 업종의 어느 규정인지"가 사라진다. 예: `(b) The owner or operator shall...`만 보면 무슨 설비 얘기인지 모른다.
   - 그래서 청크마다 50~100토큰짜리 짧은 설명(컨텍스트)을 앞에 붙인 뒤, 그 상태로 임베딩과 키워드 색인을 둘 다 만든다.

2) Anthropic이 잰 숫자
   - 상위 20개 안에 정답이 없는 비율(검색 실패율): 일반 방식 5.7%.
   - 컨텍스트 임베딩만: 3.7% (35% 감소). 컨텍스트 임베딩 + 컨텍스트 BM25: 2.9% (49% 감소). 여기에 리랭킹: 1.9% (67% 감소).
   - 컨텍스트 생성 비용: 프롬프트 캐싱 사용 시 문서 100만 토큰당 약 $1.02 (800토큰 청크, 8천 토큰 문서 기준).
   - 모델에 넘기는 청크 수는 5·10개보다 20개가 좋았다. 리랭킹은 상위 150개를 점수 매겨 20개로 줄인다.
   - 이 숫자는 Anthropic 실험값이다. 우리 수치는 [10]의 평가셋으로 다시 잰다.

3) 우리가 그대로 따르는 것
   - 하이브리드 검색: 벡터 + BM25를 둘 다 하고 순위를 합친다.
   - 컨텍스트는 임베딩 입력과 BM25 색인 둘 다에 넣는다.
   - 리랭커를 둔다. 상위 150 → 20.
   - 도메인에 맞춘 컨텍스트 프롬프트를 쓴다. Anthropic도 도메인별 프롬프트 실험을 권한다.

## [3] 문서 단위와 청크 단위 — 적재 전 확정

1) 두 단위의 뜻
   - "문서": 컨텍스트를 만들 때 모델에게 통째로 보여주는 범위. 캐싱 대상이다.
   - "청크": 실제로 임베딩되고 검색 결과로 돌아오는 조각.

2) eCFR
   - 문서 = Subpart 하나. Part 63은 업종별로 Subpart가 나뉘므로 "이 조각이 어느 업종 규정인지"를 알려면 Subpart 전체가 문맥이다.
   - 예외 규칙: gpt-4o-mini의 문맥 한도는 128k 토큰이다. 100k 토큰을 넘는 9개 Subpart는 SUU-80에서 `doc_text`를 줄여 한도 안에 맞춘다.
   - 청크 = section 하나가 기본. 예: `§ 63.1 Applicability`.
   - section이 상한(가칭 1,500토큰, `실측 후 확정`)을 넘으면 최상위 문단 `(a)`, `(b)` 경계로 나눈다. 나눈 조각마다 section 번호·제목을 반복해 붙인다. 문단 중간에서 자르지 않는다.
   - 표(`TABLE`)·부록(`appendix`)은 별도 청크로 만들고 부모 section·Subpart에 연결한다. 표를 글로 요약해 대체하지 않는다. 표 원문(markup)은 [DB 계획](<../2) db/db 구축 계획/1_eCFR 구축 계획.md>)의 `ecfr_block.markup`에 있다.
   - 수식·이미지는 그 자체로 청크를 만들지 않는다. 같은 문단 청크에 "수식/그림 있음" 표시와 `ecfr_asset` 연결만 남긴다.
   - 예약(`reserved`) 항목은 색인하지 않는다. 검색 실패가 아니라 정상 제외다.
   - 청크 하나가 Kanon 2 한도 16,384토큰을 넘는 일은 없어야 한다. 넘으면 [5]의 오류 처리로 잡는다.

3) Federal Register
   - 문서 = FR 문서 하나(`document_key`).
   - 청크 = 파서가 나눈 블록 단위. 제목+요약(abstract), DATES 블록, 개정 지시(amendatory instruction) 블록, 배경 설명은 절 단위.
   - 컨텍스트에는 문서 종류(Rule/Proposed Rule/Correction), 발행일, 시행일, 대상 Part·Subpart를 반드시 넣는다. 제안 규칙이 현행 규정처럼 검색되지 않게 하기 위해서다.

4) ADI + CAA Dashboard
   - 문서 = 회신 하나(`adi_document_version`).
   - 청크 = 질문 블록, EPA 답 블록, 조건·예외 블록, 인용 조항 블록.
   - 컨텍스트에는 회신 기관, 서명일(확정된 경우만), 요청 시설의 공정 종류, 질문 대상 Subpart와 답에서 적용/비적용으로 판단한 Subpart를 구분해 넣는다. M200005처럼 질문(VVVVVV)과 답(CCCCCCC)의 Subpart가 다른 경우가 있다.

5) ECHO
   - 청크를 만들지 않는다. `echo_program_subpart`, `echo_facility`, `echo_industry`를 SQL로 조회한다.

6) 청크가 반드시 들고 있어야 할 것 — DB 파서에 요구하는 사항
   - `release_id`: 어느 기준일 자료인지.
   - `node_key` 또는 `document_key`: 원문 항목. 예: `40/63/subpart-A/section-63.1`.
   - `block_from`, `block_to`: 어느 블록 범위를 잘라 만든 청크인지.
   - `hierarchy_path`: Part → Subpart → 중간 제목 → section 제목의 배열. 예: `["Part 63", "Subpart A—General Provisions", "§ 63.1 Applicability"]`.
   - `citation`: 사람이 읽는 인용. 예: `40 CFR 63.1(a)(1)`. 문단 경로는 `ecfr_block.label_path`에서 만든다. 추출값이므로 확신 없는 경우 section까지만 쓴다.
   - `source_locator`: 원문 XML 위치. 링크를 만들 때 쓴다.
   - 따라서 eCFR 파서는 `label_path`를 빈 값으로 두면 안 된다. 최소한 최상위 문단 `(a)`, `(b)`까지는 채워야 한다. 이 요구는 [eCFR 계획](<../2) db/db 구축 계획/1_eCFR 구축 계획.md>) 2-1의 문단 경로 규칙과 같다.

## [4] 컨텍스트 생성

1) 모델과 호출 방법
   - 모델: OpenAI `gpt-4o-mini`. 입력 $0.15, 캐시 입력 $0.075, 출력 $0.60 (백만 토큰당).
   - 문서 전체(Subpart)를 시스템 메시지에 넣는다. 1,024토큰 이상이면 시스템 메시지를 prefix로 삼는 OpenAI 자동 prefix 캐시가 적용되며, 별도 `cache_control`은 보내지 않는다.
   - Batch API는 쓰지 않는다. 청크 단위 upsert·재실행 구조와 맞지 않으므로 청크마다 일반 호출한다.
   - 1,024토큰보다 짧은 Subpart는 캐시가 안 걸릴 수 있는데, 짧으면 비용도 작으므로 그대로 둔다.

2) 프롬프트 — 법령용으로 바꾼 것
   - Anthropic 원문: "이 청크를 문서 전체 안에서 자리매김하는 짧은 설명을 써라."
   - 우리 추가 지시: 다음을 2~3문장 영어로 쓴다. (1) 어느 Subpart이고 어떤 업종·배출원을 규제하는지 (2) 이 조각이 적용대상·정의·배출한도·시험방법·모니터링·기록보고·예외·기한 중 무엇을 다루는지 (3) 어떤 설비·물질·수치 조건이 나오는지.
   - 하지 말 것: 적용 여부를 판단하는 문장, 원문에 없는 숫자, 다른 Subpart와의 비교.
   - 출력은 50~100토큰. 넘치면 잘라 쓰지 않고 다시 생성한다.
   - 프롬프트에는 버전 번호를 붙인다(`ctx_prompt_v1`). 바뀌면 [9]의 전체 재색인 규칙을 따른다.

3) 저장
   - 생성한 컨텍스트는 `rag_chunk.context_text`에 원문(`chunk_text`)과 분리해 저장한다. 원문을 고치지 않는다.
   - 임베딩 입력 = `context_text + "\n\n" + chunk_text`. BM25 색인도 같은 문자열로 만든다.
   - 사용한 모델·프롬프트 버전·생성 시각을 청크마다 남긴다.

4) 검증
   - Subpart별로 청크 3개씩 뽑아 사람이 읽는다. 다른 Subpart·다른 업종을 말하거나 적용 판단을 넣은 컨텍스트가 있으면 불합격이다.
   - 불합격이면 프롬프트를 고치고 그 Subpart만 다시 만든다.

5) 비용
   - gpt-4o-mini는 입력 $0.15, 캐시 입력 $0.075, 출력 $0.60 (백만 토큰당)이다. Part 63 전체 비용은 `실측 후 기입`.

## [5] 임베딩 — Kanon 2 Embedder

1) 왜 이 모델인가
   - 법률 문서로 학습한 임베딩 모델이다. 법률 임베딩 벤치마크 MLEB에서 1위(2025-10-16 기준), OpenAI text-embedding-3-large보다 NDCG@10이 9% 높다고 발표했다.
   - 최대 입력 16,384토큰. 규정 조문 하나를 자르지 않고 넣을 수 있다.
   - 기본 데이터로 모델 학습에 쓰지 않는다고 밝혔다.
   - 출처: [소개 글](https://isaacus.com/blog/introducing-kanon-2-embedder), [API 문서](https://isaacus.com/docs/api-reference/embeddings/embedding).

2) 호출 규격
   - `POST /embeddings`, `model=kanon-2-embedder`.
   - 색인할 때 `task=retrieval/document`, 질문을 임베딩할 때 `task=retrieval/query`. 둘을 바꾸면 검색 품질이 떨어진다.
   - 한 요청에 최대 128개 텍스트. 응답의 `usage.input_tokens`를 기록해 비용을 센다.
   - `overflow_strategy=null`로 보낸다. 기본값 `drop_end`는 한도를 넘으면 뒤를 조용히 잘라낸다. 우리는 잘리는 대신 오류로 받아 [3]의 청크 규칙을 고친다.

3) 차원
   - 기본 1,792차원. Matryoshka 방식이라 1,024·768·512·256으로 줄일 수 있고 768까지는 벤치마크 1위를 유지했다.
   - v1은 1,792로 시작한다. pgvector의 HNSW 색인은 2,000차원까지 지원하므로 문제없다.
   - 저장 공간·속도가 문제가 되면 1,024로 줄이는 것을 v2에서 실측으로 판단한다. 줄이면 전체 재임베딩이다.

4) 운영
   - 호출 제한 수치는 확인하지 못했다. 처음에는 동시 요청 1개로 시작하고 429의 `Retry-After`를 따른다.
   - 같은 `content_hash + embed_model + 프롬프트 버전`이면 다시 임베딩하지 않고 재사용한다.
   - 자체 호스팅 대안: AWS Marketplace 컨테이너로 제공된다(2025-10-29 기준). API가 막히거나 비용이 커지면 검토한다.

5) 한계
   - 영어 중심 모델이다. 한국어 질문을 그대로 임베딩하는 것은 계획에 없다.
   - 임베딩 모델을 바꾸면 전체 재색인이다. 모델 이름과 버전을 청크마다 남기는 이유다.

## [6] 키워드 검색 — BM25

1) 왜 벡터만으로 부족한가
   - 조문 번호(`63.11607`), Subpart 코드(`PPPP`), 화학물질명, 오염물질 코드 같은 정확한 문자열은 임베딩이 약하다. 규정 검색에서는 이런 질문이 많다.
   - Anthropic 실험에서도 BM25를 더했을 때 실패율이 3.7%에서 2.9%로 줄었다.

2) 방법
   - PostgreSQL 내장 전문검색을 쓴다. `rag_chunk.tsv tsvector` 컬럼에 `context_text + chunk_text`를 색인하고 `ts_rank_cd`로 점수를 낸다. Supabase에서 추가 설치 없이 된다.
   - 정확한 BM25 공식은 아니지만 v1에서는 충분하다. 실측에서 키워드 검색 실패가 두드러지면 BM25 확장 도입을 v2에서 검토한다.
   - 조문 번호·Subpart 코드는 별도 "정확 일치" 경로를 둔다. 질문에 `63.\d+` 또는 `Subpart [A-Z]{1,7}` 패턴이 있으면 해당 node를 바로 가져와 결과 맨 위에 둔다.

## [7] 검색 흐름 — 질문에서 결과까지

1) 질문 준비
   - 사용자 입력을 그대로 쓴다. 질문 재작성(LLM으로 검색용 문장 만들기)은 v1에서 하지 않는다. 평가에서 필요하면 v2에 추가한다.
   - `task=retrieval/query`로 임베딩한다.

2) 후보 모으기
   - 벡터 검색: `embedding <=> 질문벡터` 코사인 거리로 상위 150개.
   - 키워드 검색: `tsv` 점수로 상위 150개.
   - 합치기: Reciprocal Rank Fusion(k=60). 두 결과에 모두 있으면 위로 올라간다.
   - 정확 일치 경로의 결과는 합치기와 별도로 맨 위에 붙인다.

3) 리랭킹
   - Kanon 2 Reranker(Isaacus `POST /rerankings`)로 합친 상위 150개를 질문과 함께 다시 점수 매겨 20개로 줄인다.
   - 같은 회사 모델이라 API 하나로 통일된다. 법률 RAG 벤치마크 1위, 비용 $0.35/백만 토큰이라고 발표했다. 출처: [Kanon 2 Reranker](https://isaacus.com/blog/kanon-2-reranker).
   - 리랭커 효과는 [10]에서 "리랭커 없음 vs 있음"으로 잰다. 효과가 없으면 뺀다.

4) 구조 확장 — 가벼운 그래프 역할
   - 찾은 section마다 규정의 계층·참조를 따라 꼭 같이 봐야 할 조문을 덧붙인다. 벡터 점수와 무관하게 붙인다.
   - 같은 Subpart의 적용대상 section(보통 첫 section "Am I subject to this subpart?")과 정의 section("What definitions apply?").
   - Subpart A(General Provisions) 적용표. Part 63의 각 Subpart는 "Table to Subpart XX"로 General Provisions 중 무엇이 적용되는지 정한다.
   - 청크 본문이 인용하는 다른 조문(`ecfr_reference`에서 `resolution_status=resolved`인 것) 최대 5개.
   - 확장으로 붙인 조문은 "검색 결과"가 아니라 "함께 확인" 표시로 구분한다.

5) 결과 형식
   - 청크마다: 인용(`40 CFR 63.xxxx(a)`), 계층 경로, 원문, 기준일(release의 `source_as_of`), 원문 링크(기준일 고정 링크).
   - 덧붙임: 해당 section을 바꾼 FR 문서(발행일·시행일·종류), 관련 ADI/Dashboard 회신(제목·서명일·질문 대상 Subpart), ECHO에서 같은 Subpart 코드를 가진 시설 수.
   - 결과는 `common_dataset_current`가 가리키는 release에서만 읽는다. 준비 중(staging) release는 검색되지 않는다.

6) 답변 생성
   - 상위 20개 청크 + 구조 확장 조문을 Claude에 넘겨 "후보 조항, 판정 기준, 확인할 질문 체크리스트"를 만든다.
   - 생성 모델·프롬프트·인용 강제 방식은 이 문서 범위 밖이다. 백엔드 계획에서 다룬다. 다만 "모든 문장은 넘겨준 청크의 인용을 달아야 한다"는 규칙은 여기서 못 박는다.

## [8] 저장 구조 — DB 계획과의 연결

1) 재사용하는 것
   - `common_dataset_release`, `common_dataset_current`, `common_ingest_run`, `common_change_log`는 [eCFR 계획 3-5](<../2) db/db 구축 계획/1_eCFR 구축 계획.md>)의 공통 테이블을 그대로 쓴다. 색인 작업도 `common_ingest_run`에 `dataset=rag_ecfr`처럼 기록한다.
   - 원문은 `ecfr_block`, `fr_block`, `adi_block`에 있다. `rag_chunk`는 원문을 복사하되 항상 원본 위치를 가리킨다.

2) `rag_chunk` — 새로 만드는 테이블
   - `(release_id FK → common_dataset_release, chunk_key text) PK`. `chunk_key` 예: `ecfr/40/63/subpart-A/section-63.1/0`.
   - `dataset text`: `ecfr` / `fr` / `adi`.
   - `doc_key text`: 컨텍스트 생성 문서 단위. eCFR은 Subpart의 `node_key`, FR은 `document_key`, ADI/Dashboard는 `version_id`.
   - `node_key text NULL`, `block_from integer`, `block_to integer`: 원문 블록 범위. 원본 테이블에 복합 FK를 둔다.
   - `hierarchy_path text[]`, `heading text`, `citation text`, `source_locator text`.
   - `chunk_text text`, `context_text text`, `chunk_tokens integer`, `context_tokens integer`.
   - `content_hash text`: `chunk_text`의 해시. 원문이 안 바뀌었는지 판단한다.
   - `contextualizer_model text`, `context_prompt_version text`, `embed_model text`, `embed_dims integer`.
   - `embedding vector(1792)`, `tsv tsvector`.
   - `index_status text`: `pending` / `contextualized` / `embedded` / `failed`. 실패한 청크는 남기고 검색에서만 뺀다.

3) `rag_eval_case`, `rag_eval_result` — 평가용
   - `rag_eval_case`: `case_id text PK`, `question text`, `gold_citations text[]`, `gold_subparts text[]`, `source text`(adi/dashboard/manual), `source_ref text NULL`(ADI Control Number 또는 Dashboard 회신 URL), `notes text`.
   - `rag_eval_result`: `(eval_run_id, case_id) PK`, `config text`(baseline/contextual/hybrid/rerank), `release_id FK`, `first_gold_rank integer NULL`, `top20_hit boolean`, `subpart_hit boolean`, `returned_keys text[]`.

4) 인덱스
   - `embedding`: HNSW, 코사인(`vector_cosine_ops`). 처음에는 기본 매개변수로 만들고 검색 시간을 실측한 뒤 조정한다.
   - `tsv`: GIN.
   - `(dataset, release_id, doc_key)`, `(release_id, node_key)`: 구조 확장과 갱신 조회용.

5) 유의점
   - 벡터 컬럼은 release마다 따로 있다. 새 release를 만들 때 바뀌지 않은 청크의 벡터는 `content_hash + embed_model + context_prompt_version`이 같으면 복사한다.
   - 한 청크가 두 release에 있어도 저장은 두 번이다. 용량은 실측 후 이전 release 보존 정책을 정한다.

## [9] 갱신

1) 바뀐 조문만 다시 처리
   - eCFR 새 release가 공개되면 `common_change_log`에서 바뀐 `node_key`를 읽는다.
   - 바뀐 node의 청크만 다시 자르고, 컨텍스트를 다시 만들고, 다시 임베딩한다. 나머지는 [8]의 복사 규칙으로 옮긴다.
   - Subpart 제목이나 section 구성이 바뀐 경우(section 추가·삭제·번호 변경)는 그 Subpart 전체의 컨텍스트를 다시 만든다. 컨텍스트가 "문서 전체" 기준이기 때문이다.
   - FR·ADI/Dashboard도 같은 방식이다. 새 문서는 추가, 바뀐 문서는 재처리, 안 바뀐 문서는 복사.

2) 전체 재색인이 필요한 때
   - 컨텍스트 프롬프트 버전이 바뀔 때, 임베딩 모델이나 차원이 바뀔 때, 청크 규칙이 바뀔 때.
   - 새 색인을 다 만들고 [10]의 평가를 통과한 뒤에 `common_dataset_current`를 바꾼다. 이전 색인은 바로 지우지 않는다.

3) 공개 규칙
   - 색인이 끝나지 않은 release는 검색에 쓰지 않는다. DB 계획의 "완성된 묶음만 공개"와 같다.
   - 색인 실패가 있으면 실패 청크 수·이유를 `common_ingest_error`에 남기고, 실패율이 기준(가칭 0.5%, `실측 후 확정`)을 넘으면 공개를 보류한다.

4) 실행 시점
   - DB 갱신 작업이 끝난 직후 같은 스케줄러에서 이어서 실행한다. 별도 시각을 두지 않는다. 자동 갱신은 미실행이다.

## [10] 평가와 합격 기준

1) 평가셋 만들기
   - ADI/Dashboard 회신이 자연스러운 정답 자료다. Dashboard의 Part 63 명시 132건과 ADI의 Part 63 관련 문서에서 만든다.
   - 질문 = 회신의 "요청 내용"(시설·공정 설명)만 뽑아 실무자 말투로 다시 쓴다. 답 부분은 질문에 넣지 않는다.
   - 정답 = 회신이 적용/비적용 판단의 근거로 인용한 Subpart와 section. `gold_subparts`와 `gold_citations`에 나눠 둔다.
   - 회신 전체를 기계로 적재하는 것은 뒤의 일이다. 그 전에 ADI/Dashboard 회신 30건을 사람이 읽어 만든 `manual` 세트(SUU-46)로 시작한다. 파서 없이 ADI Abstract·Dashboard Affected Subpart·회신 PDF를 직접 읽는다. 적재 후 같은 방식으로 50개 이상으로 늘린다.
   - 목표 크기: 50개 이상. 업종(Subpart)이 한쪽으로 몰리지 않게 한다.

2) 지표
   - top-20 검색 실패율: 정답 section이 상위 20개 안에 없는 비율. Anthropic과 같은 지표라 숫자를 비교할 수 있다.
   - Subpart 적중률: 정답 Subpart가 상위 20개 안에 하나라도 있는 비율. 서비스가 "후보 Subpart 제시"이므로 이 지표가 더 중요하다.
   - 정답 첫 등장 순위의 중앙값.

3) 비교 순서 — 하나씩 켜면서 잰다
   - baseline: 컨텍스트 없이 벡터만.
   - contextual: 컨텍스트 붙인 벡터.
   - hybrid: contextual + BM25 합치기.
   - rerank: hybrid + Kanon 2 Reranker.
   - 각 단계의 실패율을 기록한다. 단계가 실패율을 낮추지 않으면 그 단계는 빼고 이유를 적는다.

4) 합격 기준
   - 가칭: top-20 실패율 5% 이하, Subpart 적중률 95% 이상. Anthropic의 일반 방식이 5.7%였으므로 우리 baseline을 잰 뒤 `실측 후 확정`한다.
   - 정답이 상위 20개에 없는 경우는 모두 원인을 분류한다: 청크 잘림 / 컨텍스트 오류 / 키워드 누락 / 상호참조 누락 / 정답 라벨 오류. 이 분류가 [11]의 재검토 조건이 된다.

5) 실행 결과
   - 미실행. 평가셋 수, 설정별 실패율, 원인 분류, 검색 시간(p50/p95), 청크당 비용을 기록해야 완료다.

## [11] Ontology / Knowledge Graph / Graph RAG 검토

1) 세 가지가 무엇인가
   - Ontology: "용어와 관계의 사전". 예: 도장 라인은 표면 코팅 배출원이고, 표면 코팅은 Subpart PPPP·MMMM 등에 해당한다.
   - Knowledge Graph: 그 사전대로 실제 데이터를 점과 선으로 잇는 것. 조문 ↔ Subpart ↔ 업종 ↔ 시설 ↔ 회신.
   - Graph RAG: 검색할 때 벡터만 보지 않고 선을 따라 이웃 점도 같이 가져오는 것.

2) 권고: v1에는 도입하지 않는다
   - eCFR은 이미 그래프다. Part → Subpart → section 계층, `ecfr_reference`의 상호참조, Subpart A 적용표. [7]의 "구조 확장"이 이 선을 따라 이웃을 가져온다. Graph RAG의 핵심 이득을 새 저장소 없이 얻는다.
   - 업종 ↔ Subpart 연결은 ECHO의 프로그램 코드 사전(`echo_code_map`, 예: `CAAMACT6J → Part 63 JJJJJJ`)과 NAICS 코드로 먼저 대체한다. 새 온톨로지를 쓰지 않아도 SQL 조인으로 된다.
   - 별도 그래프 DB나 온톨로지 언어를 도입하면 적재·갱신 경로가 하나 더 생긴다. 평가로 필요가 증명되기 전에는 비용만 는다.

3) 다시 검토하는 조건
   - [10]의 실패 원인 분류에서 "상호참조 누락"이 전체 실패의 큰 몫(가칭 30% 이상)을 차지할 때.
   - 사용자 질문이 "현장 용어"라서 규정 용어와 연결이 안 되는 실패가 반복될 때. 이때는 용어 사전(경량 온톨로지)부터 시작한다. 그래프 DB는 그 다음이다.
   - FR·ADI를 붙인 뒤 "이 조문의 개정 이력과 선례를 한 번에" 같은 다중 연결 질문이 서비스 요구로 확정될 때.

4) 지금 남겨두는 것
   - 위 재검토를 쉽게 하려고 `ecfr_reference`, `adi_cfr_reference`, `fr_cfr_reference`의 연결 상태(`resolution_status`)를 DB 계획대로 채운다. 이 값이 있으면 나중에 그래프로 옮기는 비용이 작다.

## [12] 데이터 적재 우선순위

1) 순서 — 이 순서대로만 진행한다
   - **1차: eCFR** — 기준 규정. 검색 코퍼스 1순위.
   - **2차: ADI + CAA** — 실무자의 실제 질문 데이터. 평가셋 기반.
   - **3차: Federal Register** — 개정 이력. 덧붙임용.
   - **4차: ECHO** — 시설 정보. 덧붙임용.

2) RAG 평가 정답지 만드는 방식 — 티켓 순서
   - **SUU-46**: RAG 평가 정답지 30건 — ADI+CAA 회신을 사람이 읽어 작성. 파서 없이, 색인 전에 한다 (완료, 32건)
   - **SUU-47~**: ADI+CAA 수집·파서 — eCFR(SUU-31~44)처럼 작은 티켓 8개쯤으로 쪼갠다. 첫 티켓 SUU-47은 Dashboard 표 읽기. 수집 5개(Dashboard 표, ADI 목록, ADI 상세, PDF 저장, 수집 실행) → 파서 3개(쪽별 글자, 40 CFR 인용, 파싱 실행)
   - **그 다음 (번호 미정)**: ADI+CAA 데이터 로딩 (실제 회신 내용을 DB에 적재)
   - **그 다음 (번호 미정)**: RAG 평가 정답지 50개+로 확장 (ADI+CAA 적재 후)
     - ADI+CAA 회신의 "질문 + EPA 답변 근거 조문"에서 질문/정답 세트 추출. SUU-46의 30건은 그대로 재사용
     - 50개 이상 평가셋 구성 (업종 분산, 양식 다양성 고려)
     - [10]의 평가 실행: baseline → contextual → hybrid → rerank

## [13] 구축 순서와 완료 조건

1) v1 — 지금
   - 이 문서 승인.
   - [3]-6의 파서 요구사항(`label_path` 최소 최상위 문단, `hierarchy_path` 생성 가능)을 eCFR 파서 티켓에 반영한다. 반영 여부는 별도 확인한다.
   - 완료 조건: DB 파서 티켓이 요구사항을 받았고, 이 문서에 `실측 후 기입` 항목 목록이 남아 있다.

2) eCFR 적재 후 — v2
   - section별 토큰 분포 측정 → 청크 상한 확정 → 20만 토큰 넘는 Subpart 목록 확정.
   - `manual` 평가셋 30건(SUU-46)은 eCFR 적재를 기다리지 않고 병행해 만든다.
   - Subpart 3개(작은 것·중간·큰 것)로 시범 색인 → 컨텍스트 표본 검수 → 비용 실측.
   - Part 63 전체 색인 → baseline/contextual/hybrid/rerank 비교 → 합격 기준 확정.
   - 완료 조건: [10]-5의 기록이 있고, 이 문서의 `실측 후 기입`이 모두 숫자로 바뀌었다.

3) ADI+CAA 적재 후
   - ADI+CAA 데이터셋 청크 규칙으로 색인.
   - 평가셋 확장 티켓(번호 미정): ADI+CAA 기반 평가셋 50개+ 작성 → [10]의 평가 실행 → 합격/재검토.
   - 완료 조건: RAG 평가 결과(top-20 실패율, Subpart 적중률, 원인 분류)가 기록되었다.

4) Federal Register 적재 후
   - FR 데이터셋 청크 규칙으로 색인 → 검색 결과의 "개정 여부·시행일" 덧붙임 검증.
   - 완료 조건: 제안 규칙이 현행 규정처럼 나오는 경우가 0건이다.

5) 자동 갱신 검증
   - 변경 없음 / 조문 1개 변경 / Subpart 구성 변경 / 프롬프트 버전 변경 / 임베딩 실패 주입 / 되돌리기를 시험한다.
   - 완료 조건: 재실행 중복 0, 실패 시 이전 색인 유지, 바뀐 조문만 재임베딩된 것이 기록으로 확인된다.

## [14] 아직 못 정한 것

1) 한국어 입력을 받을지, 받는다면 어디서 영어로 바꿀지. 서비스 타겟이 미국 공장 실무자라 v1은 영어만이다.
2) 청크 상한 토큰 수(가칭 1,500)와 벡터 차원(1,792 유지 vs 1,024). eCFR 실측 후.
3) BM25를 PostgreSQL 전문검색으로 충분한지, 확장을 붙일지. 키워드 검색 실패율 실측 후.
4) 합격 기준 숫자(가칭 5% / 95%). baseline 실측 후.
5) 이전 release 색인 보존 기간. 용량 실측 후.
6) 답변 생성 단계의 모델·프롬프트·인용 강제 방식. 백엔드 계획에서.
7) Isaacus API 호출 제한과 월 예산. 첫 시범 색인 후.

## [15] 출처

1) [Anthropic — Introducing Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval): 원칙, 실패율 수치, 비용, top-20, 리랭킹 150→20, 20만 토큰 기준.
2) [Isaacus — Introducing Kanon 2 Embedder](https://isaacus.com/blog/introducing-kanon-2-embedder): 16,384토큰, 1,792차원, Matryoshka, MLEB 순위, AWS Marketplace.
3) [Isaacus — Embedding API](https://isaacus.com/docs/api-reference/embeddings/embedding): `task`, `overflow_strategy`, `dimensions`, 128개 제한.
4) [Isaacus — Kanon 2 Reranker](https://isaacus.com/blog/kanon-2-reranker): 리랭커 존재, 가격.
5) [DB 전수조사 결과](<../2) db/db overview/2_db 전수조사 결과.md>), [eCFR 구축 계획](<../2) db/db 구축 계획/1_eCFR 구축 계획.md>), [FR 구축 계획](<../2) db/db 구축 계획/2_Federal Register 구축 계획.md>), [ECHO 구축 계획](<../2) db/db 구축 계획/3_ECHO 구축 계획.md>), [ADI+CAA 구축 계획](<../2) db/db 구축 계획/4_ADI+CAA 구축 계획.md>): 데이터 수치와 테이블 이름.
6) 모두 2026-09-14 확인.
