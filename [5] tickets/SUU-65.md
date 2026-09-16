# SUU-65 feat(db): eCFR 파싱 결과를 release로 등록한다

## 목표
파싱된 eCFR 원본 하나(as_of)를 Supabase common_* 테이블에 "이번 묶음"으로 등록하고 release_id를 돌려준다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/1_eCFR/ecfr_release.py` — `register_release(root, as_of, *, client, now=None) -> str`
- 만들 것: `[2] db/tests/1_eCFR/test_ecfr_release.py` — 이미 작성됨 (빨강 확인 완료)
- 고칠 것: `requirements.txt` — Supabase 연결용 `supabase` 패키지 추가 (Codex가 실제 실행 스크립트를 만들 때 필요. 이 티켓의 함수 자체는 `client`를 인자로 받으므로 테스트에는 필요 없음)

## 안 하는 것
- ecfr_node/ecfr_block 적재 (SUU-66)
- common_dataset_current 공개 포인터 전환
- 실제 Supabase에 붙는 실행 스크립트/CLI (이 티켓은 함수만. 다음 티켓들과 함께 나중에 진입점을 만든다)
- 실패/재시도, 동시 실행 잠금 등 세부 로직

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| as_of를 넣으면 common_ingest_run 1건, common_raw_object 2건, common_dataset_release 1건(status=staging), common_release_object 2건이 만들어진다 | `test_registers_a_new_as_of_as_run_raw_objects_release_and_release_objects` |
| 같은 as_of로 다시 부르면 새 행을 만들지 않고 기존 release_id를 그대로 돌려준다 | `test_reuses_existing_release_id_without_creating_duplicate_rows` |

## Codex 메모
- **입력**: `root`는 `ecfr_collect.py`/`ecfr_raw.py`가 쓰는 파이프라인 루트(`raw/{as_of}/manifest.json`이 있는 곳). `as_of`는 `"2026-09-10"` 같은 날짜 문자열.
- **client 인터페이스**: 실제 Supabase Python 클라이언트(`supabase-py`, `create_client(url, key)`)와 같은 모양이어야 한다.
  - 조회: `client.table(name).select(cols).eq(col, val)...execute()` → `.data`는 dict 리스트
  - 삽입: `client.table(name).insert(row).execute()`
  - 테스트의 `FakeClient`가 이 모양을 그대로 흉내낸다. 실제 실행 스크립트를 만들 때는 `create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])`로 만든 진짜 client를 넘기면 된다(`.env`에 이미 있음, service_role 키라서 RLS를 우회한다).
- **manifest_hash**: DB 스키마에 별도 manifest_hash 컬럼(1개 값)이 있는데, manifest.json에는 파일별 sha256만 있다. `sha256(f"{structure_sha256}:{xml_sha256}")`로 두 파일 해시를 합쳐서 만든다(둘 중 하나라도 바뀌면 새 release로 취급됨).
- **dataset/scope_key**: `dataset="ecfr"`, `scope_key="40/63"` 고정값 (계획 문서 예시 그대로).
- **parser_version**: `ecfr_parse.PARSER_VERSION`을 그대로 쓴다 (import만 하면 됨, parsed 파일을 직접 읽지 않아도 됨 — 이 티켓은 nodes/blocks 적재를 하지 않으므로).
- **manifest entry 읽기**: `raw/{as_of}/manifest.json`에서 `name == "title-40-structure.json"` / `"title-40-part-63.xml"` 항목을 찾는다 (`ecfr_parse._manifest_entry`와 같은 로직, 참고만 하고 직접 복붙해도 된다 — 모듈 간 private 함수 import는 하지 않는다).
- **중복 체크 순서**: `common_dataset_release`를 `(dataset, scope_key, manifest_hash, parser_version)`으로 먼저 조회하고, 있으면 그 `release_id`를 바로 반환한다(run/raw_object/release/release_object 아무것도 새로 안 만든다).
- **테이블 컬럼**: `[2] db/migrations/SUU-61_common_tables.sql`에 정확한 컬럼명이 있다.
