# SUU-79 fix(rag): 컨텍스트에 없는 이름을 지어내지 않게 한다

## 목표
`build_context_request`의 지시문에 "문서에 나온 이름을 그대로 쓰고, 지어내지 마라"는 지시를 추가한다.

## 건드릴 파일
- 고칠 것: `[2] db/pipeline/5_rag/ecfr_context.py`의 `build_context_request`
- 고칠 것: `[2] db/tests/5_rag/test_ecfr_context.py` — 이미 작성됨 (빨강 확인 완료)

## 안 하는 것
- 실제로 다시 색인해서(Claude 실제 호출) 고쳐졌는지 재검증하는 일 — 사람이 나중에 직접 확인한다
- `prompt_version` 값 자체를 바꾸는 일 (여전히 기본값 `ctx_prompt_v1`)
- `ecfr_embed.py`, `ecfr_chunk_index.py` 등 다른 파일은 건드리지 않는다

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| `build_context_request`가 만든 요청 안에 "지어내지 말라"는 지시 문구가 포함된다 | `test_instruction_tells_claude_not_to_invent_names` |

## Codex 메모
- **왜 필요한가**: SUU-76 PoC에서 실제 subpart 이름 "XXXXXX"를 Claude가 컨텍스트를 만들 때마다 "RRR"로 지어냈다(`[6] rag/PoC/SUU-76 poc 결과.md` 참고). "XXXXXX"가 플레이스홀더처럼 보여서 Claude가 "고쳐 부른" 것으로 추정된다. 검색(임베딩) 정확도엔 영향 없었지만, `context_text`를 사람이 읽는 용도로 쓰거나 나중에 답변 생성에 쓸 경우 잘못된 조문 이름을 보여주게 된다.
- **고칠 위치**: `[2] db/pipeline/5_rag/ecfr_context.py:11-17`의 `instruction` f-string. 기존 지시문 마지막 줄(`Do not decide whether the regulation applies, invent numbers absent from the source, or compare this text with another Subpart.`) 뒤에 이름을 그대로 쓰라는 문장을 추가하면 된다.
- **테스트가 확인하는 것**: `request["messages"][0]["content"]`(지시문 전체)에 "invent"와 "name"이라는 단어가 (대소문자 무관) 둘 다 포함되는지만 확인한다. 정확히 어떤 문장을 쓰든 상관없다 — 예: `"Use the exact Subpart name ... exactly as they appear ... Never invent or substitute a different Subpart name."`
- **주의**: 기존 테스트(`test_system_prompt_contains_full_document_with_cache_control` 등 4개)는 그대로 통과해야 한다 — `system`/`messages`/`prompt_version` 구조는 안 바뀐다, `messages[0]["content"]`(지시문) 텍스트만 늘어난다.
