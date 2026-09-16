# SUU-73 feat(rag): 청크 임베딩 요청을 조립한다

## 목표
컨텍스트가 붙은 청크 텍스트를 Kanon 2 Embedder에 보낼 요청을 조립한다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/5_rag/ecfr_embed.py` — `build_embedding_request(context_text, chunk_text) -> dict`
- 만들 것: `[2] db/tests/5_rag/test_ecfr_embed.py` — 이미 작성됨 (빨강 확인 완료)

## 안 하는 것
- 실제 Kanon 2 API 호출 (다음 티켓 범위)
- 응답(벡터) 파싱·저장
- 128개 배치 처리 (한 번에 여러 텍스트를 묶어 보내는 것)
- 차원 축소(Matryoshka, `dimensions` 파라미터)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 입력 텍스트가 `context_text + "\n\n" + chunk_text` 형태로 합쳐진다 | `test_input_text_joins_context_and_chunk_with_blank_line` |
| `task=retrieval/document`로 고정된다 | `test_task_is_fixed_to_retrieval_document` |
| `overflow_strategy=null`로 고정된다 | `test_overflow_strategy_is_fixed_to_null` |

## Codex 메모
- **반환 dict 모양**:
  ```python
  {
      "texts": [f"{context_text}\n\n{chunk_text}"],
      "task": "retrieval/document",
      "overflow_strategy": None,
  }
  ```
  이 모양은 Isaacus `POST /embeddings` 요청 바디와 그대로 맞도록 만든 것이다(호출은 다음 티켓에서 한다). `texts`가 리스트인 이유는 나중에(128개 배치 티켓에서) 여러 텍스트를 한 번에 넣을 수 있게 하기 위해서다. 이 티켓에서는 항상 원소 1개짜리 리스트다.
- **`task` 고정 이유**: 계획 문서([1] docs/3) rag/2_rag 구축 계획.md [5]-2절)에 따라 색인할 때는 `retrieval/document`, 검색 질문을 임베딩할 때는 `retrieval/query`를 써야 한다. 이 함수는 색인용이라 `retrieval/document`만 다룬다. 검색(질문 임베딩)은 범위 밖이다.
- **`overflow_strategy=null` 고정 이유**: 기본값 `drop_end`는 16,384토큰을 넘으면 뒤를 조용히 잘라낸다. 우리는 잘리는 대신 오류로 받아서 청크 규칙(SUU-70)을 고치는 신호로 쓴다.
- **`model`**: 이 요청 dict에는 넣지 않는다 (`model=kanon-2-embedder`는 실제 호출 시점에 다음 티켓이 채운다. SUU-71의 `prompt_version`을 요청 dict 밖에 둔 것과 같은 이유 — 이 함수는 "무엇을 보낼지"만 결정한다).
