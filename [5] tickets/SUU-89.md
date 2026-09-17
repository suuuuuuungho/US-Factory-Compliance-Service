# SUU-89 feat(rag): 컨텍스트 생성 모델을 OpenAI로 바꾼다

## 목표
`index_chunk`의 컨텍스트 생성 호출을 Claude Haiku 4.5에서 OpenAI `gpt-4o-mini`로 바꾼다. 프롬프트(`ecfr_context.py`)는 그대로.

## 건드릴 파일
- 고칠 것: `[2] db/pipeline/5_rag/ecfr_chunk_index.py` — `call_claude_api` → `call_openai_api(request, *, client=None)`, `index_chunk`의 키워드 인자 `call_claude` → `call_context`, `__all__` 갱신
- 고칠 것: `requirements.txt` — `anthropic==1.5.0` 제거, `openai==3.3.1` 추가 (로컬에 이미 설치된 버전)
- 고칠 것: `[1] docs/3) rag/2_rag 구축 계획.md` [4]절 1)·5) — 모델 `gpt-4o-mini`(입력 $0.15, 캐시 입력 $0.075, 출력 $0.60 / 백만 토큰), 캐시는 OpenAI 자동 prefix 캐시(1,024토큰 이상, 시스템 메시지가 prefix), Batch API는 안 씀(청크 단위 upsert·재실행 구조와 안 맞음), 문맥 128k라 100k 토큰 넘는 9개 Subpart는 SUU-80에서 `doc_text`를 줄인다는 예외 명시. [3]절의 "Haiku 4.5는 20만 토큰" 문구도 4o-mini 128k로 고친다
- 고칠 것: `[2] db/tests/5_rag/test_ecfr_chunk_index.py` — 이미 작성됨 (빨강 확인 완료: 7 failed, 1 passed)

## 안 하는 것
- `ecfr_context.py`(프롬프트, `ctx_prompt_v1`, `cache_control` 필드 포함 request 모양) 변경 — 호출 함수가 변환한다
- `ecfr_embed.py`, `call_kanon2_api`, `select_subpart_chunks`, 실행 스크립트(SUU-80)
- 모델 이름을 환경변수로 빼는 것 (하드코딩, 단순하게)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| `index_chunk(..., call_context=fake, call_kanon2=fake)` 호출 순서·요청 모양·저장 행이 기존과 같다 | `test_calls_context_then_kanon2_with_context_chained_into_embedding_request`, `test_saved_row_has_context_embedding_hash_and_embedded_status`, `test_index_chunk_uses_given_subpart_name_not_section_heading`, `test_index_chunk_with_none_subpart_name_omits_belongs_line` |
| `subpart_name` 빠뜨리면 `TypeError` (SUU-86 회귀 없음) | `test_index_chunk_requires_subpart_name_keyword` |
| 기본값이 `call_openai_api` / `call_kanon2_api` | `test_uses_the_real_api_callers_by_default` |
| `call_openai_api(request, client=fake)`: `model == "gpt-4o-mini"`, `messages[0] == {"role": "system", "content": doc_text}`, 그 뒤는 `request["messages"]` 그대로, `cache_control`은 안 넘김, 응답 `choices[0].message.content`를 돌려준다 | `test_call_openai_api_sends_doc_as_system_message_and_returns_text` |
| `[2] db/pipeline/5_rag/*.py`와 `requirements.txt`에 `claude-haiku-4-5`, `ANTHROPIC_API_KEY`, `anthropic`(대소문자 무관)이 없다 | `test_no_claude_left_in_pipeline_or_requirements` |

## Codex 메모
- **`call_openai_api` 시그니처**: `def call_openai_api(request: dict[str, Any], *, client: Any = None) -> str`. `client`가 `None`이면 `OpenAI(api_key=os.environ["OPENAI_API_KEY"])`를 만든다. 테스트는 `.chat.completions.create(**kwargs)`가 `.choices[0].message.content`를 가진 객체를 돌려주는 가짜를 넘긴다.
- **request 변환**: `request["system"]`은 Anthropic 모양(`[{"type": "text", "text": doc_text, "cache_control": {...}}]`)이다. `request["system"][0]["text"]`만 꺼내 `{"role": "system", "content": ...}`로 만들고, 그 뒤에 `request["messages"]`를 그대로 붙인다. `cache_control`은 OpenAI에 넘기면 안 된다(자동 prefix 캐시라 필요 없음). `request["prompt_version"]`도 안 넘긴다.
- **호출 인자**: `model="gpt-4o-mini"`, `max_tokens=256`(기존 Claude 호출과 같은 상한), `messages=[...]`. `temperature`는 기본값 그대로.
- **`ecfr_chunk_index.py` 모듈 docstring**의 "Claude" 언급도 같이 고친다(`test_no_claude_left...`가 소문자 `anthropic`만 검사하지만 문서 일관성).
- **다른 곳 `anthropic` 사용 여부**: 저장소 `.py` 중 `ecfr_chunk_index.py`만 `anthropic`을 import한다(2026-09-17 grep). `requirements.txt`에서 빼도 안전.
- **문서 [4]절**은 사실만 바꾼다. 절 구조·번호는 유지.
