# SUU-80 feat(rag): Part 63 전체를 실제로 색인한다

## 목표
eCFR Part 63 전체 조문을 실제 OpenAI(`gpt-4o-mini`)+Kanon2 API로 색인해서 `rag_chunk`를 다 채운다.

## 선행 조건 (전부 머지·완료 뒤 시작)
- SUU-86 `subpart_name` 필수 + `subpart_heading_for` (머지됨)
- SUU-84 큰 조문 `label_path` 쪼개기 (머지됨)
- SUU-89 컨텍스트 생성 OpenAI `gpt-4o-mini` (`call_context` 인자, 머지됨)
- SUU-88 본문 글자 사이 공백 제거 → SUU-87 Part 63 재적재 (같은 release 안에서 블록만 덮어씀)
- SUU-90 라벨 없는 큰 조문(Appendix A to Subpart UUUUU, 74k자) 쪼개기

## 건드릴 파일
- 새 코드 없음. `select_subpart_chunks`(SUU-76/78/85), `subpart_heading_for`(SUU-86), `index_chunk`(SUU-75/89)를 그대로 재사용한다.
- 실행 스크립트는 스크래치패드 `suu80_index.py`에만 둔다(저장소에 커밋 안 함). 완료 뒤 문서 PR 하나: 이 파일 + 계획 문서 `[1] docs/3) rag/2_rag 구축 계획.md` 75행("100k 넘는 9개 Subpart" → 조문 단위 doc_text 규칙으로 정정).

## 안 하는 것
- Part 63 외 다른 Part/Title 색인
- 새 pure function 작성

## 완료 기준 ↔ 확인 방법
| 완료 기준 | 확인 방법 |
|---|---|
| 표본 10~20개(본문 + 표 + 쪼개진 조각 섞어서) 먼저 색인해 `context_text`에 진짜 Subpart 이름이 있고 표가 `\|` 형태인지 눈으로 확인 | `suu80_index.py --sample 20` 출력(`suu80_out/sample.json`)을 사람에게 보여주고 OK |
| `rag_chunk`에 색인 대상 청크 수만큼 행, 전부 `index_status=embedded` | SQL: `select index_status, count(*) from rag_chunk where release_id = (select release_id from common_dataset_current where dataset='ecfr') group by 1` |
| "Embedding input too large" 실패 0건 | `suu80_out/failed.json`이 빈 배열 |

## 사전 조사 (2026-09-17, API 호출 없이)
- `ecfr_node` 3,771행 / `ecfr_block` 71,700행 / `rag_chunk` 0행 (release `0c2efcae-99ed-41ae-85b6-1af8c8fbc44c`)
- 대상 청크 dry-run: **5,575개** (body 2,938 / split 1,913 / table 724). SUU-90 뒤 몇 개 더 늘어남
- 조문 단위 doc_text 기준 입력 ~35M 토큰 → 캐시 없이 $5.6, 같은 조문 청크끼리 prefix 캐시되면 **$3~6**. 캡 $10
- Subpart 전체를 doc_text로 쓰면 ~$17이라 안 씀

## 실행 메모
- 호출 모양: `index_chunk(node, chunk, doc_text, subpart_name=subpart_heading_for(nodes, chunk["node_key"]), client=client)`. `node["heading"]`을 `subpart_name`에 넘기면 SUU-82 버그 재발
- **doc_text = Subpart 제목 + 그 청크가 속한 조문(node) 전체** (모든 청크 동일 규칙). 조문이 400k자를 넘으면(Appendix A to Part 63 등) `doc_text` = Subpart 제목 + 청크 자신의 텍스트 (4o-mini 128k 한도)
- Subpart가 아닌 3단계 노드 6개(`appendix-Appendix-A-to-Part-63` 등)는 `subpart_heading_for`가 `KeyError` → 그 노드 자신의 `heading`을 `subpart_name`으로 쓴다
- `select_subpart_chunks`에 넘기는 nodes에는 `reserved` 컬럼이 있어야 한다
- 행 메타: `contextualizer_model="gpt-4o-mini"`, `context_prompt_version="ctx_prompt_v1"`, `embed_model="kanon-2-embedder"`, `embed_dims=1792`, `hierarchy_path="Title 40 > {Subpart 제목} > {조문 제목}"`, `citation="40 CFR 63.NNNN"`(section만)
- `chunk` dict의 `block_nos`/`parent_chunk_key`는 upsert 전에 제거(스크립트가 새 dict를 만든다)
- Supabase 조회는 `.range()` 1,000행 페이지네이션(기본 조회는 1,000행에서 잘림)
- 이미 `rag_chunk`에 있는 `chunk_key`는 건너뛴다 → 중간에 실패해도 재실행하면 이어서 처리
- 동시 실행 4개(WinError 10035 방지), 실패 청크 3회 재시도
- 예산: dry-run 추정(문자수/4)이 캡을 넘으면 `--all`을 시작하지 않는다

## 실행 순서 (Claude)
1. `git pull` main (SUU-88·90 머지 뒤) → `suu80_index.py --dry`로 대상 수·비용 재확인
2. `--sample 20` → 컨텍스트 20개를 사람에게 보여주고 OK 받기
3. `--all` → `failed.json` 0건, SQL로 행 수·`index_status` 확인
4. 문서 PR (이 파일 + 계획 문서 75행) → Linear Done

## 실행 결과 (2026-09-17)
- `--sample 20` OK → `--all` 5,605개. OpenAI 프로젝트 지출 한도 초과(`project_spend_limit_exceeded`)로 5,137개(91%)에서 멈춤 → 두 번째 키로 488개 추가 → 분당 호출 한도(429)로 32개 실패 → 동시 실행 4개로 재실행해 0건 실패
- 최종: **`rag_chunk` 5,625행, 전부 `index_status=embedded`**, `failed.json` `[]`. Subpart 제목은 `subpart_heading_for`에서 오므로 지어내기 없음
- 비용 약 $6.5 (4o-mini 입력 ~38M 토큰). 동시 실행 16개는 마지막 10%에서 429가 몰리므로 다음엔 4~8개
- 스크립트는 재색인(새 release)에 다시 쓰므로 `[6] rag/PoC/suu80_index.py`로 저장소에 남긴다(이미 있는 `chunk_key`는 건너뛰어 재실행 가능)
