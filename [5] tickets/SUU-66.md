# SUU-66 feat(db): nodes·blocks jsonl을 ecfr 테이블에 적재

## 목표
SUU-65가 등록한 release_id로, 파싱해둔 nodes.jsonl·blocks.jsonl을 ecfr_node·ecfr_block에 실제로 넣는다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/1_eCFR/ecfr_load.py` — `load_release(root, as_of, release_id, *, client) -> None`
- 만들 것: `[2] db/tests/1_eCFR/test_ecfr_load.py` — 이미 작성됨 (빨강 확인 완료)
- 건드리지 않을 것: `ecfr_release.py` (SUU-65, 이미 병합됨)

## 안 하는 것
- ecfr_reference/ecfr_asset 적재 (파서가 references.jsonl/assets.jsonl을 아직 만들지 않음)
- common_dataset_current 공개 포인터 전환
- release 등록 자체 (SUU-65가 이미 함, 이 티켓은 release_id를 인자로 받기만 한다)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| nodes.jsonl의 각 행이 ecfr_node에 같은 건수·값으로 들어간다(release_id·source_object_id 채워짐) | `test_loads_every_node_row_into_ecfr_node_with_release_and_source_object_id` |
| blocks.jsonl의 각 행이 ecfr_block에 같은 건수·값으로 들어간다(release_id 채워짐) | `test_loads_every_block_row_into_ecfr_block_with_release_id` |
| 같은 release_id로 다시 실행해도 중복 행이 생기지 않는다 | `test_loading_the_same_release_twice_does_not_duplicate_rows` |

## Codex 메모
- **입력 파일 위치**: `root/parsed/{as_of}/{PARSER_VERSION}/nodes.jsonl`, `blocks.jsonl` (`PARSER_VERSION`은 `ecfr_parse.PARSER_VERSION`을 import). `ecfr_parse.parse_release(root, as_of)`가 이미 만들어 둔 파일이라고 가정한다 — 이 티켓에서 파서를 다시 돌리지 않는다.
- **source_object_id 구하는 법**: `load_release`의 인자로 직접 받지 않는다. `client.table("common_release_object").select("object_id").eq("release_id", release_id).eq("role", "xml").execute().data[0]["object_id"]`로 조회한다 (SUU-65가 이미 이 행을 만들어 놨다).
- **nodes.jsonl → ecfr_node 컬럼 매핑**: `node_key, parent_key, node_type, identifier, heading, reserved, sort_order, source_locator, xml_fragment, content_hash`는 그대로 옮기고, `release_id`(인자)와 `source_object_id`(위에서 조회)를 추가한다. `hierarchy_path`, `citation`은 ecfr_node에 없는 컬럼이므로 버린다.
- **blocks.jsonl → ecfr_block 컬럼 매핑**: `node_key, block_no, kind, label_path, text_content, markup, source_locator, parse_status`는 그대로 옮기고 `release_id`(인자)를 추가한다. `label_status`는 ecfr_block에 없는 컬럼이므로 버린다.
- **적재 방식**: `client.table("ecfr_node").upsert(rows, on_conflict="release_id,node_key").execute()`, `client.table("ecfr_block").upsert(rows, on_conflict="release_id,node_key,block_no").execute()`처럼 PK 컬럼으로 upsert한다 (insert가 아니라 upsert — 같은 release를 다시 돌려도 PK 충돌 없이 덮어쓰기만 된다). 행 전체를 한 번에 리스트로 넘겨도 되고 나눠서 넘겨도 된다.
- **client 인터페이스**: SUU-65와 동일하게 supabase-py 모양(`client.table(name).upsert(rows, on_conflict=...).execute()`, `.select(...).eq(...).execute()`). 테스트의 `FakeClient`가 이 모양을 흉내낸다.
- **테스트 데이터**: `[2] db/tests/1_eCFR/fixtures/`의 기존 eCFR 샘플 XML/구조 JSON을 `ecfr_parse.parse_release`로 실제로 돌려서 nodes.jsonl/blocks.jsonl을 만든다(가짜 데이터 아님). `common_release_object`는 테스트가 직접 미리 채워 넣는다(SUU-65를 실제로 부르지 않음).
