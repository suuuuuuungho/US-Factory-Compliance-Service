# RAG 검색 평가 v1 — contextual 기준선 (SUU-81)

- run_id: `2026-09-17_contextual_v1` (2026-09-17 04:35 UTC)
- config: **contextual** = gpt-4o-mini 컨텍스트(`ctx_prompt_v1`) + kanon-2-embedder(1792차원) · 검색은 `rag_chunk` 전수 코사인(파이썬) → 조문 단위로 접기 → top-20
- 색인: release `0c2efcae…`, **5,625 / 5,625 청크 (100%)**, 청크 규칙 commit `a9081bd`
- 평가셋: `rag_eval_case.jsonl` v1, 32건 (Dashboard 회신 18 + ADI 14)
- 원본 파일: `../runs.jsonl`(요약 한 줄), `2026-09-17_contextual_v1.jsonl`(케이스별)
- 실행: `python "[6] rag/eval/run_eval.py"`

## 1. 한 줄 요약

**질문 32개 중 31개는 정답 조문이 상위 20개 안에, 27개는 상위 5개 안에 들어온다. Subpart(어느 규정인지)는 상위 5개 안에서 31/32 맞춘다.** 못 맞춘 1건은 질문 말과 조문 말이 달라서다(어휘 불일치).

## 2. 지표

| 지표 | @1 | @3 | @5 | @10 | @20 |
|---|---|---|---|---|---|
| Hit loose (정답 하나라도 top-k 안) | 0.438 | 0.719 | **0.844** | 0.906 | **0.969** |
| Hit strict (정답 전부 top-k 안) | 0.094 | 0.250 | 0.281 | 0.438 | 0.625 |
| Recall (정답 중 top-k 안 비율, 케이스 평균) | 0.229 | 0.477 | 0.558 | 0.708 | 0.813 |
| Subpart Hit (primary Subpart가 top-k 안) | 0.688 | 0.844 | **0.969** | 0.969 | 1.000 |

- MRR@20 **0.618** · 첫 정답 순위 중앙값 **2**
- 95% CI (Wilson, n=32): Hit loose@5 **[0.682, 0.931]**, Hit loose@20 **[0.843, 0.994]**
- 지연: 질문 임베딩(Isaacus API) p50 572ms / p95 612ms · 검색(파이썬 전수 5,625×1792) p50 568ms — 검색 지연은 서비스 지연이 아님(서비스는 DB HNSW)

### 32건이라 조심할 것
- Hit@5 0.844는 "진짜 값이 68%~93% 사이"라는 뜻. 다른 설정과 비교할 때 5%p 차이는 우연일 수 있다(같은 케이스끼리 짝지어 McNemar로 봐야 함).
- 정답 라벨은 사람이 회신문에서 옮긴 것이라 오기·누락 가능성이 있다(F5).

## 3. 실패 분석

### 3-1. loose Hit@20 실패 — 1건

| 케이스 | 정답 | 원인 | 메모 |
|---|---|---|---|
| adi-M200005 (리튬이온 배터리 양극 슬러리 혼합) | 63.11607 (CCCCCCC) | **F3 어휘 불일치** | 정답 조문은 색인에 있음(20위 밖). 질문은 "cathode slurry / coating", 조문은 "paint and allied product manufacturing". 상위에는 PPPPPP·VVVVVV 등 비슷한 area-source 규정이 옴(F7 성격도 겹침). CCCCCCC Table 1은 8위라 Subpart는 맞춤 |

### 3-2. strict@20 실패 12건에서 보이는 패턴 (주 원인 아님, 참고)

| 패턴 | 케이스 | 뜻 |
|---|---|---|
| **Subpart A 정의 조문(63.2)이 안 잡힘** | palisades-nuclear, seepex | 회신이 "major source" 같은 일반 정의를 인용. 본문은 "this subpart"로만 가리켜 벡터로는 못 잡음 → **F4 상호참조**, 구조 확장(expand) 근거 |
| **General Provisions 성격 조문이 뒤로 밀림** | king-systems(63.4490 없음), tesla-denver(63.11175 없음), texas-eastern(63.6100/63.6095 없음) | 회신이 인용한 보조 조문(배출한도 표, 준수시점 등)은 질문 내용과 직접 안 닮음. 정답 여러 개 중 "핵심 1개"는 잡히고 나머지가 빠지는 형태 |
| **여러 Subpart에 걸친 질문** | corteva-midland(MMM/FFFF/F/G, 첫 정답 7위), dte-greenwood(UUUUU/DDDDD, 5위), adi-M170004(DDDDD/HHH, 4위) | 질문 하나에 규정 3~4개. 하나만 상위에 오고 나머지는 10위 밖 |
| **같은 Subpart 안 유사 조문 혼동** | adi-M200004(63.10042가 17위), adi-M200007(63.1503이 10위) | Subpart는 1위로 맞췄는데 정답 조문 앞에 같은 Subpart의 다른 조문(표·정의)이 여럿 옴 → **F7**, 리랭커 근거 |

### 3-3. 실패 코드 집계 (loose@20 기준)

F1 0 · F2 0 · **F3 1** · F4 0 · F5 0 · F6 0 · F7 0

## 4. 케이스별 첫 정답 순위

| 첫 정답 순위 | 건수 | 케이스 |
|---|---|---|
| 1 | 14 | ames-copper, jackson-cleaners, genesis-alkali, citation-oil-gas, cemex-knoxville, tesla-denver, buchanan-marine, materion-brush, adi-M170002, adi-M160007, adi-M150031, adi-M150028, adi-M160002, adi-M160009 |
| 2 | 9 | vicor, us-granules, hartford-finishing, texas-eastern, seepex, eaton-auburn, adi-Z200004, adi-M190019, adi-M160020 |
| 3–5 | 4 | king-systems(4), dte-greenwood(5), adi-M150020(5), adi-M170004(4) |
| 6–10 | 2 | corteva-midland(7), adi-M200007(10) |
| 11–20 | 2 | palisades-nuclear(14), adi-M200004(17) |
| 없음 | 1 | adi-M200005 |

## 5. 이 결과가 말해주는 다음 단계

1. **hybrid(BM25 + 벡터)**: F3 1건 + "정확한 조문 번호·용어"가 들어간 질문에서 벡터만으로는 놓치는 보조 조문 회수. strict/Recall 개선 기대.
2. **rerank(Kanon reranker)**: 같은 Subpart 안 유사 조문 혼동(adi-M200004 17위, adi-M200007 10위, palisades 14위). MRR·Hit@5 개선 기대.
3. **expand(구조 확장)**: Subpart A 정의(63.2), 적용대상 조문 자동 추가. strict 실패 중 F4 패턴 대응.
4. **합격선 확정**: 계획 [13]-1의 가칭(top-20 실패 ≤1건, Subpart 실패 ≤1건)을 이 run은 둘 다 만족. baseline(컨텍스트 없음) 재임베딩 비교가 남아 있음 — "컨텍스트가 실제로 도움됐는가"는 아직 증명 안 됨.

## 6. 이력

- 같은 날 색인 91%(5,137청크) 상태에서 먼저 돌렸을 때는 Hit loose@5 0.625 / @20 0.750, 실패 8건 중 7건이 F1(정답 조문 미색인: Subpart XXXXXX·YYYY·ZZZZZ·YYYYY 통째로 없음). 색인을 100% 채운 뒤 재실행한 것이 이 문서. 그 run 파일은 삭제함.
