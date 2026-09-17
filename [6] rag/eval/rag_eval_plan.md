# RAG 검색 평가 계획 (rag_eval_plan)

- 작성일: 2026-09-17
- 상태: 평가 재설계 중(2026-09-17). 색인·검색 코드는 유지하고 평가 단계만 처음부터 다시 정한다. 정한 것은 [14]에 순서대로 적는다.
- 상위 문서: `[1] docs/3) rag/2_rag 구축 계획.md` [10] 평가와 합격 기준. 이 문서는 그 절을 실행 가능한 수준으로 구체화한 것이다. 둘이 다르면 이 문서를 따르고 상위 문서를 고친다.
- 관련 티켓: SUU-46(평가셋), SUU-76(PoC 검색), SUU-81(1차 측정), SUU-101(리랭커), SUU-100(hybrid), SUU-116(BM25), SUU-117(채점표), SUU-115(평가셋 v2 — 접음), 대시보드 SUU-113.

---

## [0] 한 줄 요약

**"공장 설명 질문을 넣었을 때, 정답 조문이 검색 결과 상위 몇 번째에 나오는가"**를 조합(`vector` → `reranker` → `hybrid`)마다 같은 채점표(Hit@5, Hit@20, nDCG@10, Recall@20)로 재고, 숫자와 실패 원인을 남겨 품질이 어떻게 좋아졌는지 보여준다. 판정 단위는 조문(Subpart는 보조).

---

## [1] 평가가 답해야 하는 질문

| # | 질문 | 왜 필요한가 | 답하는 지표 |
|---|---|---|---|
| Q1 | 정답 조문이 상위 k개 안에 나오는가 | 답변 생성 단계는 상위 20개만 본다. 여기 없으면 답을 못 만든다 | Hit@k, Recall@k, top-20 실패율 |
| Q2 | 정답 Subpart(업종 규정)를 찾는가 | 서비스의 1차 출력이 "후보 Subpart 제시"다 | Subpart Hit@k |
| Q3 | 정답이 얼마나 위에 있는가 | 리랭커·구조 확장 필요 여부 판단 | **nDCG@10**(주), MRR(v1 비교용), 첫 정답 순위 중앙값 |
| Q4 | 설정을 바꿨을 때 정말 좋아졌는가(우연이 아닌가) | 32건은 작다. 차이가 통계적으로 의미 있는지 봐야 한다 | 쌍대 비교(McNemar), 신뢰구간 |
| Q5 | 틀린 건 왜 틀렸나 | 다음에 무엇을 고칠지 정한다 | 실패 원인 분류표 |
| Q6 | 얼마나 걸리고 얼마나 드는가 | 배포 가능한지 판단 | 검색 지연 p50/p95, 질문당 비용 |

---

## [2] 평가셋 — `[6] rag/eval/rag_eval_case.jsonl`

### 2-1. 무엇인가
- EPA ADI(Applicability Determination Index) 14건 + CAA Dashboard 회신 18건 = **32건**. 사람이 원문 회신을 읽고 만들었다(SUU-46).
- 한 행 = `case_id`, `question`, `gold_subparts`, `gold_citations`, `source`, `source_ref`, `notes`.
- `question`: 회신의 "요청 내용"(시설·공정 설명)만 실무자 말투로 다시 씀. 조문 번호·Subpart 코드는 질문에 없음(`test_question_does_not_leak_answer`가 검사).
- `gold_citations`: 회신이 판단 근거로 인용한 조문. **83개**, 전부 `40 CFR 63.xxxx(...)` 형식. 문단 번호가 붙은 것 29개.
- `gold_subparts[0]`: 질문의 주 Subpart. 한 Subpart 최대 3건(`MAX_PER_SUBPART`).

### 2-2. 통계 (2026-09-17)
| 항목 | 값 |
|---|---|
| 케이스 수 | 32 (adi 14, dashboard 18) |
| 정답 인용 수 | 83 (케이스당 1개: 8건, 2개: 7, 3개: 9, 4개: 6, 5개: 2) |
| 정답 Subpart 수 | 31개 서로 다른 Subpart. 케이스당 1개: 20건, 2개: 10, 3개: 1, 4개: 1 |
| Subpart A(General Provisions) 포함 | 2건 (palisades-nuclear, seepex) |

### 2-3. 한계 — 결과를 읽을 때 반드시 같이 말할 것
1. **n=32는 작다.** 히트율 1건 차이 = 3.1%p. 그래서 [6]의 신뢰구간·쌍대 비교를 반드시 붙인다.
2. **정답은 "적용 판단의 근거 조문"이지 "검색이 찾아야 할 유일한 조문"이 아니다.** 예: 정의 조문(`63.2`)은 인용되지 않았지만 검색되면 유용할 수 있다. 정답이 아닌 상위 결과가 "틀린 것"이라고 단정하지 않는다(정밀도는 재지 않는 이유).
3. **라벨 오류 가능성.** 사람이 읽고 옮긴 것이라 조문 번호 오기·누락이 있을 수 있다. 실패 분석([7])에서 `정답 라벨 오류`를 별도 범주로 두고, 확인되면 평가셋을 고치고 버전을 올린다(`eval_set_version`).
4. **질문이 회신 원문을 요약한 것**이라 실제 사용자 질문보다 정보가 많을 수 있다(낙관적 편향). v2에서 짧은 질문 변형을 추가한다([10]).
5. Subpart 편중은 막았지만(최대 3건) **31개 Subpart / 전체 약 130개**만 덮는다. 나머지 Subpart의 품질은 모른다.

### 2-4. 버전 관리
- 파일을 고치면 `eval_set_version`을 올린다(`v1` = 2026-09-11 32건). 결과 파일마다 어느 버전으로 쟀는지 적는다.
- 확장 목표: 50건 이상(상위 문서 [10]-1). 확장은 별도 티켓. **확장 전후 숫자는 섞어 비교하지 않는다.**
- 2026-09-17: gpt-4o-mini 초안으로 100건까지 늘리려던 SUU-115는 접었다(초안 452건은 `rag_eval_case_v2.draft.jsonl`에 참고용으로만 남김, 커밋 안 함).
- **v2 = `rag_eval_case_v2.jsonl` 102건**(SUU-120): v1 32건 + 새 70건. 새 건은 SUU-115 초안 중 근거 문장이 회신에 100% 그대로 있는 243건 → 주 Subpart당 v1 포함 2건까지 75건 → Claude가 회신 원문과 대조(70 채택, 5 제외, 17 손봄). 주 Subpart 68개. 세부: `[5] tickets/SUU-120.md`. 앞으로의 측정은 v2로 하고 v1 숫자와 섞지 않는다.

---

## [3] 판정 단위와 히트 규칙 — 여기가 제일 엄밀해야 한다

### 3-1. 비교 단위 = 조문(section)
- 정답 `"40 CFR 63.4481(a)(1)"` → 문단 번호를 떼고 `section-63.4481`로 만든다. (`citation_section_key`)
- 이유: 청크는 조문(또는 조문 조각) 단위이고, 문단 번호 수준으로는 청크가 나뉘지 않는다. 문단 단위 판정은 v1에서 하지 않는다.
- Table/Appendix 정답은 현재 평가셋에 없다. 생기면 `node_key`의 마지막 조각과 문자열 비교하는 같은 규칙을 쓴다.

### 3-2. 청크 → 조문 대응
- 검색 결과 청크의 `node_key`(예 `40/63/subpart-PPPP/section-63.4481`)의 마지막 조각이 정답 section key와 같으면 "그 조문의 청크"다.
- 한 조문이 여러 청크(`/0`, `/0-1`, … 본문 조각, `/1`, `/2`… 표)로 나뉘어 있어도 **그중 하나라도** 상위 k에 있으면 그 조문은 찾은 것이다.
- **순위는 청크 순위가 아니라 조문 순위로 센다.** 같은 조문의 청크가 상위에 여러 개 있으면 하나로 접는다(dedupe by node_key). 즉 "top-5"는 **서로 다른 조문 5개**를 뜻한다. 이래야 조문이 50조각으로 쪼개진 정의 조문이 top-k를 독차지해 다른 조문을 밀어내는 효과가 지표를 왜곡하지 않는다.
  - 청크 단위 순위도 함께 저장하되(`returned_chunk_keys`), 보고 지표는 조문 단위로 한다.

### 3-3. 케이스 히트 — 느슨한 기준과 엄격한 기준

**채점표(SUU-117 확정, 2026-09-17)**: 보고는 네 자로 한다 — **Hit@5, Hit@20, nDCG@10, Recall@20**. MRR은 v1 비교용으로만 표에 남긴다. 나머지 지표는 결과 파일에 계속 저장하되 보고표에는 쓰지 않는다.

| 이름 | 정의 | 용도 |
|---|---|---|
| **loose Hit@k** (채점표: k=5, 20) | 정답 조문 중 **하나라도** 상위 k 조문 안에 있음 | 답변 생성이 시작될 수 있는가 |
| **strict Hit@k** (참고) | 정답 조문 **전부**가 상위 k 안에 있음 | 근거를 빠짐없이 모았는가 |
| **Recall@k** (채점표: k=20) | (상위 k 안에 있는 정답 조문 수) / (정답 조문 수) — 케이스별로 계산해 평균 | 후보 모으기 진단: 낮으면 벡터/BM25 문제 |
| **nDCG@k** (채점표: k=10, **주 점수**) | 정답은 전부 1점(등급 없음). DCG = Σ 1/log2(순위+1), IDCG = 정답 수만큼 1등부터 채운 값. 케이스별 DCG/IDCG 평균 | 정답 여러 개가 위에 얼마나 모였나. Recall@20 높고 nDCG@10 낮으면 순서(리랭커) 문제 |
| **Subpart Hit@k** | 상위 k 조문의 Subpart 집합에 `gold_subparts[0]`(주 Subpart)이 있음 | Q2. 서비스 1차 출력 |
| **Subpart Hit@k (any)** | `gold_subparts` 중 하나라도 있음 | 참고 |

### 3-4. 순위 지표
- **첫 정답 순위(first_gold_rank)**: 정답 조문 중 가장 위에 있는 것의 조문 순위(1부터). 상위 K_max 안에 없으면 `null`.
- **MRR@K** = 평균(1 / first_gold_rank), 없으면 0. 첫 정답만 보므로 v1 비교용으로만 남긴다(SUU-117).
- **중앙값 첫 정답 순위**: `null`은 K_max+1로 놓고 중앙값을 낸다(보수적).

### 3-5. K 값
- **검색 풀 K_max = 20**: 모든 설정에서 상위 20 조문(중복 접은 뒤)을 저장한다. 그러면 k = 1, 3, 5, 10, 20 지표를 나중에 다시 실행 없이 계산할 수 있다.
- 청크는 조문 20개를 채울 때까지 가져온다(청크로는 보통 30~60개). 벡터 검색에서 청크 상위 150개를 받아 접는다.
- **보고 기본 k**: SUU-81은 **top-5**(티켓 그대로). 상위 문서의 합격 기준은 **top-20**. 둘 다 같은 결과 파일에서 나온다.

### 3-6. 동점·결정성
- 코사인 점수 동점이면 `chunk_key` 오름차순으로 고정한다. 같은 입력이면 같은 결과가 나와야 한다.
- 질문 임베딩은 실행마다 API를 부른다. 임베딩이 미세하게 달라질 수 있으므로 **질문 임베딩을 파일로 저장**(`rag_eval_query_embeddings.json`)하고 재사용한다. 결과 재현 시 API를 다시 부르지 않는다.

---

## [4] 비교할 설정(config)

조합 이름(SUU-117부터 `run_eval.py --config` 값): **`vector`** = contextual 색인 벡터만, **`reranker`** = vector + Kanon 2 리랭커, **`hybrid`** = vector + BM25 + RRF + 리랭커. 아래 표의 `contextual`/`rerank`는 각각 `vector`/`reranker`의 옛 이름이며 `runs.jsonl`의 지난 run에는 옛 이름이 남아 있다.

| config | 검색 방식 | 필요한 준비 | 티켓 |
|---|---|---|---|
| `baseline` | 컨텍스트 **없이** `chunk_text`만 임베딩 → 벡터 | 청크 5,625개를 컨텍스트 없이 다시 임베딩(Kanon만, LLM 비용 없음). `rag_chunk`와 별도 컬럼/테이블(`embedding_nocontext`)에 저장 | 후속 |
| `contextual` | `context_text + chunk_text` 임베딩 → 벡터 (지금 `rag_chunk.embedding`) | SUU-80 완료 | **SUU-81** |
| `rerank` | contextual 벡터 상위 150 청크 → Kanon 2 Reranker → 20 | Isaacus rerank 호출 | **SUU-101** |
| `hybrid` | contextual 벡터 + BM25(파이썬 `rank_bm25`, SUU-116) → RRF(k=60) → 리랭커 | 키워드 검색 함수(SUU-99 ts_rank → SUU-116 BM25로 교체) | SUU-100 (rerank 뒤) |
| `expand` | rerank + 구조 확장(적용대상 조문·정의 조문·Subpart A 표) | `ecfr_reference` | 후속, 상위 문서 [7]-4 |

순서 변경(2026-09-17): 원래 hybrid → rerank였으나 rerank → hybrid로 바꿈. SUU-81 실측에서 문제는 후보 부족(loose Hit@20 31/32)이 아니라 순서(strict Hit@5 0.281, MRR 0.618)였고, SUU-99에서 키워드가 벡터보다 나은 케이스는 5/32뿐이라 RRF 단독 효과가 불확실하다. 리랭커가 들어간 뒤 "리랭커 후보를 벡터만 vs 벡터+키워드"로 비교한다.

규칙:
- 한 번에 **하나만** 바꾼다. 앞 단계와 같은 질문 임베딩·같은 release·같은 평가셋 버전으로 잰다.
- 단계가 nDCG@10을 올리지 못하면 뺀다(Hit@20·Recall@20이 떨어져도 뺀다). 판단은 [6]의 쌍대 비교로 한다.
- `contextual`이 **첫 기준선**이다(baseline은 재임베딩이 필요해 뒤로 미룸). 발표에서는 "PoC(SUU-76) → 문제 발견·수정 → contextual 측정 → 이후 단계"로 흐름을 보여준다([11]).

---

## [5] 실행 절차 (한 config, 한 run)

```
1. 입력 고정
   - release_id = common_dataset_current(ecfr)  → 결과에 기록
   - eval_set_version, config, embed_model, contextualizer_model, context_prompt_version, 청크 규칙 버전(git commit) 기록
2. 질문 임베딩
   - build_query_embedding_request(question) → task="retrieval/query", kanon-2-embedder
   - 32개 저장(재사용)
3. 검색
   - config별 후보 수집 → 청크 순위 → 조문 순위로 접기 → 상위 20 조문
   - 케이스마다 청크 상위 목록, 조문 상위 목록, 점수, 소요 시간(ms) 저장
4. 판정
   - citation_section_key, is_hit(loose/strict), first_gold_rank, subpart_hit
5. 집계
   - k = 1,3,5,10,20 별 지표, MRR@20, 중앙값 순위, 지연 p50/p95, 비용
6. 실패 분석
   - loose Hit@20 실패 케이스마다 원인 범주 1개 + 메모
7. 기록
   - results/<run_id>.jsonl, runs.jsonl 한 줄 추가, Linear 티켓에 요약 표
```

- 검색은 v1에서는 `rag_chunk` 전체(release 하나, `index_status='embedded'`)를 파이썬으로 받아 `rank_chunks_by_similarity`로 계산한다(5,625 × 1792차원 — 메모리 약 80MB, 케이스당 1초 이내). DB의 HNSW 인덱스 검색(`<=>`)은 서비스 단계에서 쓰고, 그때 **두 방식의 순위가 같은지** 한 번 대조한다(근사 검색 오차 확인).
- 지연 시간은 "질문 임베딩 API + 검색"을 따로 잰다. 파이썬 전수 계산 지연은 서비스 지연이 아니므로 표에 구분해 적는다.

---

## [6] 통계적 엄밀성 — 32건으로 말할 수 있는 것과 없는 것

1. **신뢰구간**: 모든 비율(Hit@k, Subpart Hit@k)에 Wilson 95% 구간을 붙인다. n=32에서 대략:
   - 90.6% (29/32) → [75.8%, 96.8%]
   - 75.0% (24/32) → [57.9%, 86.7%]
   - 즉 "90% vs 85%"는 구간이 겹친다. 숫자 하나로 우열을 말하지 않는다.
2. **설정 간 비교는 쌍대(paired)로**: 같은 32문항을 두 설정이 풀었으므로, 케이스별 (A만 맞음 / B만 맞음 / 둘 다 / 둘 다 틀림) 2×2 표를 만들고 **McNemar 정확 검정**(불일치 쌍의 이항검정)을 쓴다. p < 0.05면 "차이 있음", 아니면 "차이를 확인할 수 없음"이라고 쓴다. MRR 차이는 케이스별 1/rank 차이의 **부트스트랩 95% 구간**(10,000회)으로 본다.
3. **평가셋에 맞춰 튜닝하지 않는다**: 프롬프트·청크 규칙을 바꿀 때 32건의 실패 사례를 보고 고치면 그 32건에서만 좋아질 수 있다(과적합). 고친 뒤에는 (a) 어떤 케이스를 보고 고쳤는지 적고, (b) 평가셋을 50건 이상으로 늘렸을 때 다시 잰다. 늘린 케이스가 사실상 hold-out이 된다.
4. **결과 표에 항상 같이 적는 것**: n, 성공 수, 비율, 95% CI. 비교 표에는 불일치 쌍 수와 p값.

---

## [7] 실패 원인 분류 (loose Hit@20 실패 + strict 실패 중 눈에 띄는 것)

| 코드 | 범주 | 뜻 | 확인 방법 |
|---|---|---|---|
| F1 | 청크 문제 | 정답 조문이 색인에 없거나(빈 청크 제외·실패), 조각이 너무 잘게/크게 나뉘어 의미가 흩어짐 | `rag_chunk`에서 node_key 조회, 조각 수·길이 |
| F2 | 컨텍스트 오류 | context_text가 잘못된 Subpart·내용을 말함 | 정답 청크의 context_text 읽기 |
| F3 | 어휘 불일치 | 질문의 말(공정명·물질명)과 조문 표현이 달라 벡터가 못 잡음. BM25/리랭커로 해결 기대 | 정답 청크 텍스트에 질문 핵심어가 있는지 |
| F4 | 상호참조 | 정답이 다른 Subpart(예: Subpart A, 정의 조문)이고 본문이 "this subpart"로만 가리킴 → 구조 확장 필요 | gold_subparts에 A 등 포함 여부 |
| F5 | 정답 라벨 오류 | 회신 인용 오기·누락 | 원문 회신 재확인 → 평가셋 수정 + 버전 업 |
| F6 | 질문 정보 부족 | 질문에 업종·공정이 충분히 안 적힘 | 질문 다시 읽기. 평가셋 수정 대상 아님(실제 사용자도 그럴 수 있음) |
| F7 | 유사 규정 혼동 | 다른 Subpart의 비슷한 조문(예: 여러 산업의 "What are my emission limits?")이 위에 옴 | 상위 결과 목록의 Subpart 분포 |

- 케이스당 주 원인 하나만 고른다. 둘 이상이면 메모에 적는다.
- 분류 결과를 세어 "다음 단계로 무엇을 켤지"의 근거로 쓴다. 예: F3가 많으면 hybrid, F4가 많으면 expand, F7이 많으면 rerank.

---

## [8] 결과 파일 형식 — 대시보드가 그대로 읽는다

v1은 파일. 나중에 DB 테이블(`rag_eval_run`, `rag_eval_result`)로 옮길 때 **필드를 그대로** 쓸 수 있도록 지금부터 같은 이름을 쓴다.

### 8-1. `[6] rag/eval/runs.jsonl` — run 하나에 한 줄 (대시보드의 시계열 축)
```json
{
 "run_id": "2026-09-17_contextual_v1",
 "run_at": "2026-09-17T09:00:00Z",
 "config": "contextual",
 "eval_set_version": "v1",
 "n_cases": 32,
 "release_id": "0c2efcae-…",
 "embed_model": "kanon-2-embedder",
 "contextualizer_model": "gpt-4o-mini",
 "context_prompt_version": "ctx_prompt_v1",
 "chunk_rule_commit": "d02bd7f",
 "k_max": 20,
 "metrics": {
   "hit_loose": {"1": 0.0, "3": 0.0, "5": 0.0, "10": 0.0, "20": 0.0},
   "hit_strict": {"5": 0.0, "20": 0.0},
   "recall": {"5": 0.0, "20": 0.0},
   "subpart_hit_primary": {"5": 0.0, "20": 0.0},
   "mrr_20": 0.0,
   "median_first_gold_rank": 0,
   "ci95_hit_loose_5": [0.0, 0.0],
   "ci95_hit_loose_20": [0.0, 0.0]
 },
 "latency_ms": {"embed_p50": 0, "embed_p95": 0, "search_p50": 0, "search_p95": 0},
 "cost_usd": {"per_query": 0.0, "total": 0.0},
 "failure_counts": {"F1": 0, "F2": 0, "F3": 0, "F4": 0, "F5": 0, "F6": 0, "F7": 0},
 "notes": "…"
}
```

### 8-2. `[6] rag/eval/results/<run_id>.jsonl` — 케이스 하나에 한 줄
```json
{
 "run_id": "2026-09-17_contextual_v1",
 "case_id": "dashboard-king-systems-2020-06-16",
 "gold_sections": ["section-63.4481", "section-63.4581", "section-63.4490"],
 "gold_subparts": ["PPPP"],
 "returned_sections": ["section-63.4481", "…"],          // 조문 순위, 최대 20
 "returned_chunk_keys": ["ecfr/40/63/subpart-PPPP/section-63.4481/0", "…"],
 "returned_scores": [0.63, "…"],
 "returned_subparts": ["PPPP", "…"],                       // returned_sections와 같은 길이
 "first_gold_rank": 1,
 "gold_ranks": {"section-63.4481": 1, "section-63.4581": 7, "section-63.4490": null},
 "hit_loose_5": true, "hit_strict_5": false, "recall_5": 0.33,
 "hit_loose_20": true, "hit_strict_20": false, "recall_20": 0.67,
 "subpart_hit_primary_5": true,
 "latency_ms": {"embed": 0, "search": 0},
 "failure_code": null,                                      // hit_loose_20 == false일 때 F1~F7
 "failure_note": null
}
```

### 8-3. 나중에 DB로 옮길 때
- `rag_eval_run` = 8-1 한 줄, `rag_eval_result` = 8-2 한 줄(`(run_id, case_id)` PK). 상위 문서 [8]-3의 컬럼 이름(`first_gold_rank`, `top20_hit`→`hit_loose_20`, `subpart_hit`, `returned_keys`)은 이 문서 기준으로 맞춘다.
- 평가셋 자체도 `rag_eval_case` 테이블로 옮기되, 원본은 계속 jsonl(git으로 이력 관리).

---

## [9] 결과 기록 (실측 후 채움)

| run_id | config | eval_set | Hit@5 loose (CI) | Hit@20 loose (CI) | strict@20 | Subpart Hit@5 | MRR@20 | 중앙값 순위 | 실패 F1~F7 |
|---|---|---|---|---|---|---|---|---|---|
| 2026-09-17_contextual_v1 (SUU-81) | contextual | v1 | 0.844 [0.682, 0.931] | 0.969 [0.843, 0.994] | 0.625 | 0.969 | 0.618 | 2 | F3 1 |
| 2026-09-17_rerank_v1 (SUU-101) | rerank | v1 | 0.906 [0.758, 0.968] | 0.969 [0.843, 0.994] | 0.750 | 0.938 | 0.725 | 1 | F3 1 (같은 케이스) |

- 색인 5,625/5,625(100%). 세부: `results/rag_eval_result.md`.

새 채점표(SUU-117부터). 지난 run과 같은 결과 파일에서 다시 계산할 수 있으므로 옛 run도 이 표에 옮겨 적는다.

| run_id | 조합 | eval_set | Hit@5 | Hit@20 | nDCG@10 | Recall@20 | MRR(비교용) | 비용/32건 |
|---|---|---|---|---|---|---|---|---|
| 2026-09-17_vector_v1 (SUU-117) | vector | v1 | 0.844 | 0.969 | 0.573 | 0.812 | 0.618 | $0 |
| 2026-09-17_reranker_v1 (SUU-119) | reranker | v1 | 0.906 | 0.969 | 0.658 | 0.885 | 0.725 | $1.99 |
| 2026-09-17_hybrid_v1 (SUU-119) | hybrid(BM25) | v1 | 0.906 | 0.969 | 0.666 | 0.909 | 0.725 | $2.79 |

- reranker → hybrid: 31건 동일, 1건 좋아짐, 0건 나빠짐. 32건으로는 판정 불가 → hybrid 채택은 평가셋을 늘린 뒤. 세부: `results/rag_eval_result.md`.
- 지연: 질문 임베딩 p50 572ms / p95 612ms, 파이썬 전수 검색 p50 568ms(서비스 지연 아님).

비교 표(설정 A vs B): 불일치 쌍(A만/B만), McNemar p, MRR 차이 부트스트랩 CI.

| A vs B | 지표 | A만 | B만 | McNemar p | MRR 차이 (부트스트랩 95% CI) | 판정 |
|---|---|---|---|---|---|---|
| contextual vs rerank | Hit loose@5 | 1 | 3 | 0.625 | +0.107 [-0.006, 0.220] | **rerank 채택** (13 좋아짐/4 나빠짐, 나빠진 건 1~4칸). 세부: `results/rag_eval_result.md` |
| contextual vs rerank | Hit strict@5 | 2 | 5 | 0.453 | | 비용 질문당 $0.062, 검색 지연 p50 4.4초 |

---

## [10] 대시보드 설계 메모 (별도 티켓)

목적: "품질이 어떻게 좋아졌는가"를 발표·운영에서 한눈에 보여준다. 데이터 원천은 [8]의 두 파일(또는 그 DB 테이블) — **대시보드는 계산하지 않고 읽기만 한다.**

1. **품질 추이(메인)**: x = run(시간·config 순), y = Hit@5 / Hit@20 / Subpart Hit@5 / MRR. 점마다 95% CI 오차막대. config 색 구분. 여기서 "PoC → contextual → hybrid → rerank" 상승을 보여준다.
2. **케이스 히트맵**: 행 = 32 케이스, 열 = run. 셀 = first_gold_rank(1=진초록 … null=회색). 어떤 케이스가 계속 안 잡히는지 보인다.
3. **순위 분포**: run 하나의 first_gold_rank 히스토그램(1, 2-3, 4-5, 6-10, 11-20, 없음).
4. **실패 원인 파이/막대**: F1~F7 개수. run 간 비교.
5. **케이스 상세**: 클릭 → 질문, 정답, 상위 20 조문(정답은 강조), 정답 청크의 context_text, failure_note.
6. **비용·지연 카드**: 질문당 비용, 지연 p50/p95, 색인 비용(청크당) — 색인 run(SUU-80) 숫자와 함께.
7. **필터**: eval_set_version, config, source(adi/dashboard), Subpart.

구현 후보는 대시보드 티켓에서 정한다(예: 정적 HTML + jsonl 로드, 또는 Supabase 테이블 + 간단한 웹). 이 문서는 **무엇을 보여줄지와 데이터 형식**만 고정한다.

---

## [11] 발표용 "품질 개선 흐름" 스토리 (시간순)

| 단계 | 무엇을 했나 | 발견 | 고친 티켓 |
|---|---|---|---|
| PoC (SUU-76, 9/16) | Subpart XXXXXX 11개 청크 색인, 질문 1개 검색 → 정답 1위 | ① 표만 있는 빈 청크 ② Subpart 이름 지어냄("RRR") | SUU-78, 79 |
| 1차 전체 색인 시도 (9/16) | 955개 색인 | ③ 이름 문제 여전(호출측이 조문 제목을 넘김) ④ 88k자 청크 임베딩 실패 ⑤ 동시 15개 소켓 오류 | SUU-82→86, 84, 90 |
| 파서 점검 | 원문 텍스트 검사 | ⑥ 글자 사이 공백(`( 1 )`) ⑦ 표 셀 구분 없음 | SUU-88, 83, 87 |
| 컨텍스트 모델 교체 (SUU-89) | Haiku → gpt-4o-mini | 비용 1/3, 품질 동일(표본) | SUU-89 |
| 2차 전체 색인 (SUU-80, 9/17) | 5,625 청크, 약 $6, 20분 | 표본 20개 이름 정확 20/20 | — |
| **1차 측정 (SUU-81)** | contextual, 32건 | (숫자) | — |
| 이후 | baseline / hybrid / rerank / expand 비교 | (숫자) | 후속 |

발표 슬라이드 순서 제안: 문제(정답 없는 검색은 못 믿는다) → 평가셋(어떻게 만들었나·한계) → 지표 정의(그림 하나로 loose/strict/Subpart) → 개선 흐름 표 → 추이 그래프 → 실패 분석 → 다음 단계.

---

## [12] SUU-81 범위 (이 계획에서 1차로 하는 것)

Codex(순수 함수 + 테스트):
- `build_query_embedding_request(question) -> dict` — `task="retrieval/query"`, `overflow_strategy=None`
- `citation_section_key(citation) -> str` — `"40 CFR 63.4481(a)(1)"` → `"section-63.4481"`
- `section_key_of_chunk(chunk_key_or_node_key) -> str` — `node_key` 마지막 조각
- `rank_sections(ranked_chunks, k_max=20) -> list[dict]` — 청크 순위를 조문 순위로 접기(첫 등장 유지, 점수 = 최고 점수)
- `gold_ranks(gold_citations, ranked_sections) -> dict[str, int | None]`
- `is_hit(gold_citations, ranked_sections, top_k=5, strict=False) -> bool`
- `summarize(results, ks=(1,3,5,10,20)) -> dict` — Hit loose/strict, Recall, MRR, 중앙값, Wilson CI

Claude(실행):
- 32건 질문 임베딩 → 검색 → [8] 형식으로 저장 → 표 → 실패 분류 → Linear 기록.
- 티켓 완료 기준은 top-5 표 하나지만, **결과 파일에는 top-20까지** 저장한다(재실행 없이 나머지 지표 계산 가능).

안 하는 것(후속): baseline 재임베딩, hybrid, rerank, 대시보드, 평가셋 확장.

---

## [13] 아직 정하지 않은 것
1. 합격선. nDCG@10 기준으로, 세 조합을 새 채점표로 잰 뒤 정한다. 정하면 CI가 최신 run을 검사하는 티켓을 낸다.
2. `baseline` 임베딩을 어디에 저장할지(별도 테이블 vs 컬럼 추가). 재임베딩 티켓에서 정한다.
3. ~~평가셋을 어떻게 만들지~~ → v2 102건으로 확정(SUU-120). 더 늘릴 때는 같은 방법(초안 → 100% 근거 일치 → 사람 대조).
4. hybrid 채택 여부. BM25로 바뀐 뒤(SUU-116) 아직 안 쟀다.
5. RRF 가중치. 지금은 1:1. 평가셋이 커진 뒤 Recall@150이 부족하면 조정.

---

## [14] 평가 재설계 — 정한 순서 (2026-09-17)

색인(A)과 검색(B)은 그대로 두고 평가(C)만 처음부터 다시 정한다. 한 번에 하나씩, 이해한 단위까지만.

| # | 정한 것 | 결과 |
|---|---|---|
| C-1 | 무엇을 재나 | 질문 → 정답 **조문**이 몇 번째로 나오나. Subpart는 보조(조문을 맞히면 Subpart는 자동으로 맞음) |
| C-2 | 채점표 | **Hit@5, Hit@20, nDCG@10(주), Recall@20**. 정답 등급 없이 전부 1점. MRR은 v1 비교용 (SUU-117) |
| C-2' | 조합 이름 | `vector` / `reranker` / `hybrid`. 셋 다 contextual 색인을 쓴다. 키워드 쪽은 ts_rank → BM25 (SUU-116) |
| C-3 | 평가셋 | **v2 102건** (SUU-120). 100% 근거 일치 초안 → Subpart당 2건 → 사람(Claude) 대조 |
| C-4 | 세 조합 재측정 | 완료(SUU-119, [9]). reranker nDCG@10 0.658, hybrid 0.666 — 1건 차이 |
| C-5 | 합격선 + CI 검사 | C-4 뒤 |
| C-6 | hybrid 채택 여부 | C-4 뒤 |

그 뒤: 답변 생성(아직 없음), 대시보드(SUU-113), ADI 회신 `adi_` 테이블 적재.

검색 쪽에서 더 해볼 수 있는 것(평가셋이 생긴 뒤, 효과 순 추정): 정확 일치 경로(질문의 `63.xxxx`·`Subpart 코드` 바로 올리기, 공짜) → 질문 다시 쓰기(LLM으로 검색용 문장) → LLM 리랭커(Kanon과 비교) → RRF 가중치 → 색인 자체 변경(조각 크기·설명 프롬프트·임베딩 모델, 비쌈).
