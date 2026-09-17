# SUU-81 feat(rag): 32건 평가셋으로 검색 정확도를 측정한다

## 목표
평가셋 32건의 검색 결과를 **조문 단위**로 판정·집계하는 순수 함수를 만든다. 실제 검색 실행과 결과 파일 저장은 Claude가 한다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/5_rag/ecfr_eval.py`
- 테스트(이미 있음, 수정 금지): `[2] db/tests/5_rag/test_ecfr_eval.py`

## 안 하는 것
- 실제 API·DB 호출, 검색 실행 스크립트, `runs.jsonl`/`results/*.jsonl` 저장 (Claude가 함)
- `ecfr_embed.py`, `ecfr_index_run.py` 등 기존 파일 수정
- baseline/hybrid/rerank 비교, 대시보드, 평가셋 수정
- `tests/` 아래 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 질문 임베딩 요청은 `task="retrieval/query"`, `overflow_strategy=None` | `test_query_request_uses_retrieval_query_task` |
| `"40 CFR 63.4481(a)(1)"` → `"section-63.4481"` (문단 번호·공백 무시), 조문이 아니면 `ValueError` | `test_citation_section_key_drops_paragraph`, `test_citation_section_key_rejects_non_section` |
| 청크의 `node_key` 마지막 조각이 section key | `test_section_key_of_chunk_is_last_node_key_piece` |
| 같은 조문의 청크는 하나로 접고, 점수 = 최고 점수, 그 청크의 `chunk_key`·Subpart 기록 | `test_rank_sections_collapses_chunks_of_same_section`, `test_rank_sections_keeps_best_chunk_and_score_per_section` |
| 조문 `k_max`개까지만 반환 | `test_rank_sections_cuts_at_k_max` |
| 점수 내림차순, 동점은 `chunk_key` 오름차순, 입력 순서와 무관 | `test_rank_sections_breaks_ties_by_chunk_key`, `test_rank_sections_sorts_by_score_regardless_of_input_order` |
| 정답 조문별 순위(1부터), 없으면 `None`, 같은 조문 인용 여러 개는 키 하나 | `test_gold_ranks_are_section_ranks_starting_at_one`, `test_gold_ranks_none_when_missing_and_dedupes_same_section` |
| loose = 하나라도 top-k 안, strict = 전부 top-k 안 | `test_is_hit_loose_needs_any_gold_in_top_k`, `test_is_hit_strict_needs_all_gold_in_top_k` |
| `summarize`: Hit loose/strict, Recall, Subpart Hit(primary)를 k별로 | `test_summarize_hit_loose_per_k`, `test_summarize_hit_strict_and_recall`, `test_summarize_subpart_hit_primary` |
| MRR@20, 첫 정답 순위 중앙값(없으면 21) | `test_summarize_mrr_and_median_rank` |
| Hit loose@5·@20에 Wilson 95% CI, 0%·100%에서도 [0,1] 안 | `test_summarize_wilson_ci_for_hit_loose`, `test_summarize_wilson_ci_at_boundaries` |
| `n_cases` 포함 | `test_summarize_reports_n_cases` |

## Codex 메모
- 규칙 원본: `[6] rag/eval/rag_eval_plan.md` [3](판정), [8](필드 이름). 이 파일과 다르면 계획 문서를 따른다.
- 기존 코드: `[2] db/pipeline/5_rag/ecfr_embed.py`의 `build_embedding_request`가 문서용 요청 모양. 질문용도 같은 모양에 `task`만 다르다.
- 입력 청크는 `ecfr_index_run.rank_chunks_by_similarity` 출력(`chunk_key`, `node_key`, `score` 포함). `chunk_key`는 `ecfr/` 접두사 + `node_key` + `/조각번호`.
- `rank_sections` 출력 한 줄: `{"section_key", "chunk_key", "subpart", "score"}`. `subpart`는 `node_key` 3번째 조각 `subpart-PPPP`에서 `PPPP`. 접기 전에 `(-score, chunk_key)`로 정렬해 결정적으로 만든다.
- `summarize(results, ks=(1, 3, 5, 10, 20), k_max=20)` 입력 한 줄: `{"gold_ranks": {section_key: int|None}, "gold_subparts": [..], "returned_subparts": [..]}`. 출력 키(계획 [8]-1 `metrics`와 같음): `n_cases`, `hit_loose`, `hit_strict`, `recall`, `subpart_hit_primary`(각각 `{str(k): 비율}`), `mrr_20`, `median_first_gold_rank`, `ci95_hit_loose_5`, `ci95_hit_loose_20`(`[lo, hi]`).
  - first_gold_rank = `gold_ranks` 값 중 최소(None 제외). 없거나 `k_max` 초과면 MRR 기여 0, 중앙값 계산 시 `k_max + 1`.
  - Recall@k = (rank ≤ k 인 정답 수) / (정답 수), 케이스별 계산 후 평균.
  - Subpart Hit(primary)@k = `gold_subparts[0] in returned_subparts[:k]`.
  - Wilson: z = 1.96. `center = (p + z²/2n) / (1 + z²/n)`, `half = z·sqrt(p(1-p)/n + z²/4n²) / (1 + z²/n)`. 결과를 `[0, 1]`로 자른다.
- 표준 라이브러리만 쓴다(`math`, `statistics`, `re`). numpy 금지.
- `citation_section_key`는 정규식 `63\.\d+` 하나면 된다. 없으면 `ValueError`.
