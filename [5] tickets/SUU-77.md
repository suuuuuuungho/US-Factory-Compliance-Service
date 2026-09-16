# SUU-77 fix(db): 대량 데이터 적재 시 upsert timeout 수정

## 목표
`ecfr_load.py`의 node/block upsert를 여러 번 나눠 보내서, 대량 데이터에서도 Postgres statement timeout이 나지 않게 한다.

## 건드릴 파일
- 고칠 것: `[2] db/pipeline/1_eCFR/ecfr_load.py` — `load_release` 안의 두 upsert 호출을 배치로 나눈다
- 고칠 것: `[2] db/tests/1_ecfr/test_ecfr_load.py` — 이미 수정됨 (빨강 확인 완료). `FakeClient`에 `upsert_call_sizes` 기록 기능 추가, 새 테스트 `test_batches_large_upserts_to_avoid_statement_timeout` 추가
- 건드리지 않을 것: `ecfr_release.py`, `ecfr_publish.py`, `ecfr_ingest.py` (배선은 그대로 유지)

## 안 하는 것
- 재시도/부분 실패 복구 로직 (한 배치가 실패하면 그냥 예외를 던진다. 복구는 다음 과제)
- 다른 파이프라인(`adi_details_run.py` 등)의 upsert 방식 변경
- 배치 크기를 설정 가능하게 만들기 (상수로 고정해도 된다)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| block이 많아도(1,200개) 여러 번의 upsert 호출로 나눠 보낸다. 한 번에 보내는 개수가 1,000개를 넘지 않는다 | `test_batches_large_upserts_to_avoid_statement_timeout` |
| 나눠 보내도 결과는 기존과 동일하다 (모든 행이 들어간다) | `test_batches_large_upserts_to_avoid_statement_timeout` (같은 테스트가 개수도 확인) |
| node upsert도 같은 방식으로 배치 처리한다 | `test_batches_large_upserts_to_avoid_statement_timeout` |
| 기존 동작(적재 내용 정확성, 재적재 시 중복 없음)이 그대로 유지된다 | 기존 3개 테스트 (수정 없음, 계속 통과해야 함) |

## Codex 메모
- **실제로 발생한 오류**: SUU-72(실제 데이터 첫 적재) 실행 중 `postgrest.exceptions.APIError: {'message': 'canceling statement due to statement timeout', 'code': '57014', ...}`. 원인은 `ecfr_block` upsert 한 번에 71,700행을 보낸 것. `ecfr_node`는 3,771행이라 이번엔 통과했지만, 안전하게 같이 배치 처리한다.
- **고치는 법**: `node_rows`/`block_rows`를 만든 뒤, `client.table(...).upsert(...).execute()` 한 번 호출하던 것을 `for i in range(0, len(rows), BATCH_SIZE): ... upsert(rows[i:i+BATCH_SIZE], ...).execute()`처럼 나눠 호출한다. `BATCH_SIZE`는 500 정도로 상수를 둔다(테스트는 1,000 이하만 확인하므로 500이든 1,000이든 통과한다).
- **테스트가 쓰는 가짜 데이터**: 실제 fixture XML은 너무 작아서(block 13개) 배치가 필요 없다. 그래서 이 테스트는 파서를 거치지 않고 `nodes.jsonl`/`blocks.jsonl`을 직접 합성해서 1,200줄을 만든다(`write_synthetic_parsed_files`). `load_release`는 파일만 읽으므로 이 방식이 그대로 통한다.
- **`FakeClient.upsert_call_sizes`**: 테스트 파일에 이미 추가됨. `client.table(name).upsert(rows, ...)`가 호출될 때마다 `len(rows)`를 기록한다. 실제 supabase-py에는 없는, 테스트 전용 기능이다.
- **release 복구**: 지금 실제 Supabase의 release(`0c2efcae-99ed-41ae-85b6-1af8c8fbc44c`, as_of 2026-09-11)는 `staging`에 멈춰있고 node는 이미 들어가 있다. 이 티켓이 merge된 뒤 SUU-72를 다시 실행하면, `upsert(on_conflict=...)`라 node는 중복 없이 재적용되고 block부터 이어서 들어간다. `register_release`도 같은 manifest면 기존 release_id를 재사용하므로 그대로 이어서 실행하면 된다.
