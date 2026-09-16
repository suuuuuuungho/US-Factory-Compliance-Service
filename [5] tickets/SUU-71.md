# SUU-71 feat(rag): 청크 컨텍스트 생성 요청을 조립한다

## 목표
청크 하나를 Claude Haiku에게 보내 컨텍스트를 생성시킬 요청(문서 전체를 캐싱된 시스템 프롬프트로, 청크를 유저 메시지로)을 조립한다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/5_rag/ecfr_context.py` — `build_context_request(doc_text, chunk_text, *, prompt_version="ctx_prompt_v1") -> dict`
- 만들 것: `[2] db/tests/5_rag/test_ecfr_context.py` — 이미 작성됨 (빨강 확인 완료)
- 고칠 것: 없음 (`pyproject.toml`의 `[2] db/pipeline/5_rag` pythonpath는 SUU-70에서 이미 추가됨)

## 안 하는 것
- 실제 Claude API 호출 (다음 티켓 범위. 네트워크가 필요해 여기서는 테스트하지 않는다)
- 응답 파싱, `rag_chunk.context_text`/`context_tokens`에 저장
- Message Batches API 사용
- 50~100토큰 상한 검증, 캐시 최소 길이(512~4096토큰) 처리
- 프롬프트 문구의 세부 워딩 검증 (계획 문서 [4]-2의 3가지 요구사항을 지시문에 담되, 정확한 문장은 Codex 재량. 테스트는 문서/청크가 올바른 자리에 들어가는지만 확인한다)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 시스템 프롬프트에 문서 전체가 들어가고 cache_control이 설정된다 | `test_system_prompt_contains_full_document_with_cache_control` |
| 유저 메시지에 청크 텍스트가 들어간다 | `test_user_message_contains_the_chunk_text` |
| 프롬프트 버전 문자열을 반환한다(기본값 ctx_prompt_v1) | `test_returns_the_prompt_version_for_storage` |
| 프롬프트 버전을 인자로 바꿀 수 있다 | `test_prompt_version_can_be_overridden` |

## Codex 메모
- **반환 dict 모양**:
  ```python
  {
      "system": [{"type": "text", "text": doc_text, "cache_control": {"type": "ephemeral"}}],
      "messages": [{"role": "user", "content": "..."}],
      "prompt_version": prompt_version,
  }
  ```
  이 모양은 `anthropic` 파이썬 SDK의 `client.messages.create(system=..., messages=...)` 인자와 그대로 맞도록 만든 것이다(호출은 다음 티켓에서 한다).
- **유저 메시지 내용**: 계획 문서(`[1] docs/3) rag/2_rag 구축 계획.md` [4]-2절)의 지시사항을 담는다 — (1) 어느 Subpart이고 어떤 업종·배출원을 규제하는지 (2) 적용대상/정의/배출한도/시험방법/모니터링/기록보고/예외/기한 중 무엇을 다루는지 (3) 어떤 설비·물질·수치 조건이 나오는지. 2~3문장 영어로 쓰라고 지시하고, 적용 여부 판단·원문에 없는 숫자·다른 Subpart 비교는 하지 말라고 명시한다. `chunk_text`는 이 지시문 안에 포함시켜 보낸다(테스트는 `messages[0]["content"]`에 `chunk_text`가 포함되는지만 확인).
- **doc_text/chunk_text 출처**: 이 티켓은 문자열만 받는다. `doc_text`(Subpart 전체 텍스트)와 `chunk_text`(SUU-70의 `build_chunks` 결과로 만든 청크 원문)를 실제 DB에서 조합하는 것은 다음 티켓(적재) 범위다.
- **모델 이름**: `claude-haiku-4-5`. 이 티켓에는 등장하지 않는다(요청 dict에 model을 안 넣음 — 호출 시점에 다음 티켓이 채운다).
