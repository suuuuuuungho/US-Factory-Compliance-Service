# SUU-68 feat(db): eCFR 전체 적재를 한 번에 실행

## 목표
as_of 하나로 register_release → load_release → publish_release를 순서대로 실행하고 release_id를 반환한다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/1_eCFR/ecfr_ingest.py` — `run_ecfr_ingest(root, as_of, *, client, register_release=register_release, load_release=load_release, publish_release=publish_release) -> str`
- 만들 것: `[2] db/tests/1_eCFR/test_ecfr_ingest.py` — 이미 작성됨 (빨강 확인 완료)
- 건드리지 않을 것: `ecfr_release.py`, `ecfr_load.py`, `ecfr_publish.py` (SUU-65/66/67, 이미 병합됨)

## 안 하는 것
- 실패 시 부분 롤백/재시도 (계획 문서의 "일부만 들어감 → staging/failed 유지"는 다음 단계 과제)
- 실제 Part 63 데이터로 첫 실행 (이 티켓은 함수만 만든다. 사람이 나중에 CLI에서 실제로 돌린다)
- 동시 실행 잠금

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| register_release → load_release → publish_release 순서로, 같은 release_id를 이어서 호출한다 | `test_calls_register_load_publish_in_order_and_threads_the_release_id` |
| 기본값으로는 실제 SUU-65/66/67 함수를 쓴다(주입 안 하면 진짜 동작) | `test_uses_the_real_functions_by_default` |

## Codex 메모
- **왜 함수 자체가 아니라 순서/배선만 테스트하나**: 각 단계(register/load/publish)의 정확성은 SUU-65/66/67에서 이미 테스트로 검증됐다. 이 티켓은 세 함수를 올바른 순서·인자로 연결하는 "배선"만 새로 만드는 것이라 그것만 확인한다.
- **주입 패턴**: `adi_details_run.run(adi_root, details_root, *, fetch_details=fetch_details, today=None)`과 같은 방식 — 기본값은 실제 함수(`ecfr_release.register_release` 등)를 가리키게 하고, 테스트에서만 키워드 인자로 가짜를 넘긴다. 모듈 최상단에서 `from ecfr_release import register_release` 식으로 import해서 그 이름을 기본값으로 쓰면 된다.
- **인자 순서 주의**: `load_release(root, as_of, release_id, *, client)`는 release_id가 세 번째 위치 인자다. `publish_release(release_id, *, client)`는 release_id만 위치 인자로 받는다(참고: `[2] db/pipeline/1_eCFR/ecfr_publish.py`).
- **반환값**: `register_release`가 돌려준 release_id를 그대로 반환한다(새로 만들었든 기존 걸 재사용했든 동일).
