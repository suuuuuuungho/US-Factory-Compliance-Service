# SUU-82 fix(rag): 컨텍스트 생성 시 실제 Subpart 이름을 알려준다

## 목표
`build_context_request`가 실제 Subpart 이름을 인자로 받아 프롬프트에 명시해서, 모델이 이름을 지어내지 않게 한다.

## 건드릴 파일
- `[2] db/pipeline/5_rag/ecfr_context.py` — `build_context_request`에 키워드 인자 `subpart_name: str | None = None` 추가. 값이 있으면 instruction(user 메시지) 맨 앞에 `"This chunk belongs to {subpart_name}."` 같은 문장을 넣어 실제 이름을 명시한다. `None`이면 지금과 동일하게 동작(하위 호환).
- `[2] db/pipeline/5_rag/ecfr_chunk_index.py` — `index_chunk`가 `build_context_request` 호출 시 `node["heading"]`을 `subpart_name`으로 넘긴다.

## 안 하는 것
- 이미 색인된 358개 청크 재색인 (SUU-80 후속 작업에서 진행)
- Part 63 나머지 색인(SUU-80) 재개 (이 티켓 머지 후 별도로 진행)
- doc_text 자체를 바꾸는 것 (본문은 그대로, 이름만 instruction에 추가로 알려줌)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| `build_context_request`에 실제 subpart 이름을 넘기면, 반환되는 프롬프트 텍스트 안에 그 이름이 그대로 포함된다 | `test_instruction_states_the_real_subpart_name` |
| subpart 이름을 안 넘기면 예전처럼 동작한다(하위 호환) | `test_works_without_a_subpart_name` |

## Codex 메모
- `node` dict에는 이미 `heading` 필드가 있다 (`ecfr_node.heading`, 예: `"Subpart XXXXXX—National Emission Standards for ..."` 형태). `index_chunk`에서 이 값을 그대로 `subpart_name`으로 넘기면 된다.
- 프롬프트에 이름을 넣는 위치는 `system`(캐시되는 doc_text)이 아니라 `messages`의 user instruction 쪽이 낫다 — instruction은 원래 캐싱 대상이 아니고, 청크마다 다시 보내는 부분이라 매번 넣어도 캐시 히트율에 영향 없다.
- 기존 "이름을 지어내지 마라" 지시문(`test_instruction_tells_claude_not_to_invent_names`)은 그대로 유지한다 — 이번 수정은 그 지시에 "정답"을 실제로 제공하는 것이지, 지시 자체를 대체하는 게 아니다.
