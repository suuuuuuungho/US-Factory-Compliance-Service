# SUU-76 PoC 결과 — Subpart XXXXXX 실제 색인·검색

- release_id: `0c2efcae-99ed-41ae-85b6-1af8c8fbc44c`
- subpart: `40/63/subpart-XXXXXX`
- 실행일: 2026-09-16
- 사용 API: Claude Haiku 4.5(컨텍스트), Kanon 2 Embedder(임베딩, Isaacus)

## 1. 색인 결과

`select_subpart_chunks`로 뽑은 청크 12개 중, 표(table)만 있고 본문 텍스트가 없는 빈 청크 1개(`appendix-Table-1.../0`)를 제외한 **11개**를 실제로 색인해 `rag_chunk`에 넣었다.

| chunk_key | citation | chunk_text 길이 | context_text 길이 |
|---|---|---|---|
| section-63.11516/0 | 40 CFR 63.11516 | 28,172 | 1,124 |
| section-63.11517/0 | 40 CFR 63.11517 | 5,638 | 915 |
| section-63.11519/0 | 40 CFR 63.11519 | 14,571 | 1,196 |
| section-63.11514/0 | 40 CFR 63.11514 | 5,430 | 1,119 |
| section-63.11515/0 | 40 CFR 63.11515 | 351 | 708 |
| appendix-Table-1.../1 (표) | Table 1 to Subpart XXXXXX | 5,429 | 673 |
| appendix-Table-2.../0 | Table 2 to Subpart XXXXXX | 161 | 455 |
| appendix-Table-2.../1 (표) | Table 2 to Subpart XXXXXX | 758 | 783 |
| section-63.11521/0 | 40 CFR 63.11521 | 1,684 | 821 |
| section-63.11522/0 | 40 CFR 63.11522 | 12,977 | 941 |
| section-63.11523/0 | 40 CFR 63.11523 | 133 | 530 |

11개 행 모두 `context_text`, `embedding`(1792차원), `content_hash`가 채워졌고 `index_status = "embedded"`다.

**발견한 엣지 케이스**: `Table 1 to Subpart XXXXXX`의 기본(본문) 청크는 표 블록만 있고 본문 블록이 없어 `chunk_text`가 빈 문자열이었다. 빈 텍스트를 Claude에 보내면 "Unable to Process: empty chunk" 응답이 왔다 — 색인 대상에서 제외해야 한다. (SUU-76/SUU-70 스펙에는 없던 케이스라 실행 중 발견, 실행 스크립트에서 빈 청크를 걸러내는 것으로 처리함.)

## 2. 컨텍스트 표본 3개 육안 검토

**샘플 1 — section-63.11516 (What are my standards and management practices?)**
> This chunk belongs to **40 CFR Part 63, Subpart RRR**, which regulates metal fabrication and finishing operations at area sources... 이하 표준·관리기준 설명.

**샘플 2 — section-63.11517 (What are my monitoring requirements?)**
> This chunk belongs to **40 CFR Part 63, Subpart RRR**... 이하 모니터링(EPA Method 22/9) 설명.

**샘플 3 — section-63.11514 (Am I subject to this subpart?) — 정답 조문**
> This chunk belongs to **Subpart RRR**, which regulates metal fabrication and finishing operations at area sources... 이하 적용대상 9개 카테고리, MFHAP 정의 설명.

**판단**: 세 샘플 모두 다른 Subpart 내용이 섞이거나("다른 Subpart 얘기") 컨텍스트 안에서 "그래서 당신은 적용된다/안 된다" 같은 적용 판단을 내리는 문장은 없다. 각 청크가 다루는 내용을 요약하는 데 그친다 — 이 기준은 통과.

**⚠️ 발견한 문제**: Claude가 생성한 컨텍스트 11개 전부에서 실제 이름인 "**Subpart XXXXXX**" 대신 "**Subpart RRR**"이라는 존재하지 않는 이름을 일관되게 지어냈다. 짐작되는 원인은 "XXXXXX"가 플레이스홀더처럼 보여 Claude가 실제 subpart 코드로 "고쳐" 부른 것으로 보인다. 검색(임베딩) 결과 자체에는 영향이 없었지만(아래 3번 참고), `context_text`를 사람에게 그대로 보여주는 용도로 쓸 경우 잘못된 조문 번호를 보여주게 되므로 후속 티켓에서 프롬프트에 "subpart 이름을 절대 바꾸지 말고 그대로 써라" 같은 지시를 추가하는 게 필요하다.

## 3. 벡터 검색 결과

평가셋 질문 `dashboard-vicor-2020-04-16` (정답 조문: `40 CFR 63.11514(a)`)로 검색한 결과, top 5:

| 순위 | score | citation | chunk_key |
|---|---|---|---|
| 1 | 0.6320 | **40 CFR 63.11514** ✅ | section-63.11514/0 |
| 2 | 0.6240 | Table 1 to Subpart XXXXXX | appendix-Table-1.../1 |
| 3 | 0.5731 | 40 CFR 63.11522 | section-63.11522/0 |
| 4 | 0.5551 | Table 2 to Subpart XXXXXX | appendix-Table-2.../1 |
| 5 | 0.5506 | 40 CFR 63.11523 | section-63.11523/0 |

정답 조문(`40 CFR 63.11514(a)`)이 코사인 유사도 1위로 나왔다 — **이 기준 통과**.

## 4. 결론

- ✅ Subpart XXXXXX 청크가 모두 `rag_chunk`에 실제로 들어감 (11/12, 빈 청크 1개 제외)
- ✅ 컨텍스트가 다른 Subpart 내용이나 적용 판단을 섞지 않음
- ⚠️ 컨텍스트가 subpart 이름("XXXXXX")을 "RRR"로 잘못 지어내는 문제 발견 — 검색 정확도에는 영향 없었지만 사람이 읽는 용도로 쓸 때는 고쳐야 함
- ✅ 평가셋 질문으로 검색했을 때 정답 조문이 1위로 나옴

**다음 액션(후속 티켓 후보)**: 컨텍스트 생성 프롬프트(`ctx_prompt_v1`)에 "문서에 나온 이름을 그대로 쓰고 지어내지 마라" 지시 추가.

## 부록 — 원본 데이터
같은 폴더의 `suu76_rows.json`(색인된 11개 행 전체), `suu76_search.json`(검색 top 5 원본)에 원본 데이터를 남겼다.
