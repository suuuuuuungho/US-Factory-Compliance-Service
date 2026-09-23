# SUU-70 feat(rag): eCFR 조문을 청크 단위로 나눈다

## 목표
ecfr_node/ecfr_block 데이터에서 section/appendix 하나 = 청크 하나 규칙으로 RAG 청크 목록을 만든다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/5_rag/ecfr_chunks.py` — `build_chunks(nodes, blocks) -> list[dict]`
- 만들 것: `[2] db/tests/5_rag/test_ecfr_chunks.py` — 이미 작성됨 (빨강 확인 완료)
- 고칠 것: `pyproject.toml` — `pythonpath`에 `"[2] db/pipeline/5_rag"` 추가 (이미 반영됨)

## 안 하는 것
- 컨텍스트 생성(Claude 호출) — SUU-71
- Kanon 2 임베딩 — SUU-72
- rag_chunk 테이블 적재 — SUU-73/74
- 16,384토큰 초과 처리, `doc_key`/`hierarchy_path`/`citation` 등 rag_chunk의 나머지 컬럼 채우기 (이 티켓은 "어떻게 자르는지"만 정한다. 나머지 컬럼은 적재 티켓에서 원본 node/block 조회로 채운다)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| reserved가 아닌 section/appendix마다 청크가 정확히 1개씩 생긴다 | `test_creates_one_base_chunk_per_non_reserved_section_or_appendix` |
| reserved 표시된 node는 청크 목록에서 빠진다 | `test_excludes_reserved_nodes_entirely` |
| TABLE block은 본문과 분리된 별도 청크로 만들어지고 부모 청크를 가리킨다 | `test_splits_table_blocks_into_separate_chunks_linked_to_their_parent` |
| 표가 있는 section의 본문 청크는 표 block_no를 포함하지 않는다 | `test_table_section_body_chunk_excludes_the_table_block_number` |

## Codex 메모
- **반환 dict 모양** (이 티켓 한정, rag_chunk 컬럼 전체가 아니다):
  ```python
  {
      "chunk_key": "ecfr/{node_key}/{순번}",  # 기본 청크는 순번 0, 표 청크는 1부터
      "node_key": node_key,
      "block_nos": [정수 block_no, ...],       # 오름차순
      "parent_chunk_key": None,                 # 표 청크만 부모(기본 청크)의 chunk_key
  }
  ```
  `chunk_key` 형식은 계획 문서(`[1] docs/3) rag/2_rag 구축 계획.md` [8]절)의 예시 `ecfr/40/63/subpart-A/section-63.1/0`를 그대로 따른다.
- **대상 node**: `node_type`이 `"section"` 또는 `"appendix"`이고 `reserved`가 `false`인 것만. `part`/`subpart`/`subject_group`은 청크를 만들지 않는다(문서 구조 노드일 뿐).
- **표 분리**: 같은 node_key의 block들 중 `kind == "table"`인 것만 따로 청크로 뺀다. 나머지(표가 아닌) block_no들이 기본 청크의 `block_nos`가 된다. 표가 없는 node는 기본 청크 하나만 생긴다.
- **테스트가 쓰는 실제 사례**: `[2] db/tests/1_eCFR/fixtures/ecfr_part63_sample.xml`을 `ecfr_parse.parse_release`로 돌리면 `40/63/subpart-G/section-63.110`에 block_no 1~13 중 5번만 표다. 이 케이스로 "표 분리"와 "chunk_key 형식"을 둘 다 확인한다.
- **수식·이미지**: 이 티켓에서는 아무 처리도 안 한다 — `kind`가 `formula`/`image`인 block은 그냥 기본 청크의 `block_nos`에 포함된다(계획 문서: "부모 문단 청크에 표시만" 하는 세부 로직은 다음 단계).
