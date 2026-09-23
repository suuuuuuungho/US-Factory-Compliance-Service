# SUU-67 feat(db): 검증된 release를 공개 포인터로 전환

## 목표
release_id 하나를 공개(published) 상태로 바꾸고 common_dataset_current 포인터가 그 release를 가리키게 한다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/1_eCFR/ecfr_publish.py` — `publish_release(release_id, *, client, now=None) -> None`
- 만들 것: `[2] db/tests/1_eCFR/test_ecfr_publish.py` — 이미 작성됨 (빨강 확인 완료)

## 안 하는 것
- 적재 결과 검증(건수 일치, 고아 연결 확인) — 이 함수는 "이미 검증 끝난 release"를 받는다고 가정
- 실패 시 롤백, 동시 실행 잠금
- 이전 release의 status를 되돌리거나 지우는 것 (계획 문서: 원문 근거로 쓰인 release는 유지한다)

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| release_id를 넘기면 common_dataset_release.status가 published로 바뀌고 published_at이 채워진다 | `test_publishing_sets_release_status_and_published_at` |
| common_dataset_current(dataset, scope_key)가 이 release_id를 가리킨다 | `test_publishing_points_common_dataset_current_to_the_release` |
| 다른 release_id로 다시 공개해도 이전 release 행은 지워지지 않고 남아있다 | `test_publishing_a_new_release_replaces_the_pointer_but_keeps_old_release_row` |

## Codex 메모
- **순서**: 1) `client.table("common_dataset_release").select("dataset,scope_key,source_as_of").eq("release_id", release_id).execute().data[0]`로 dataset/scope_key/source_as_of를 읽는다. 2) 같은 테이블에 `.update({"status": "published", "published_at": timestamp}).eq("release_id", release_id).execute()`. 3) `client.table("common_dataset_current").upsert({...}, on_conflict="dataset,scope_key").execute()`로 포인터를 채운다.
- **common_dataset_current 컬럼**: `dataset, scope_key, release_id, last_checked_at, latest_source_as_of` (PK는 `(dataset, scope_key)`). `latest_source_as_of`는 방금 읽은 release의 `source_as_of`를 그대로 쓴다.
- **now 인자**: SUU-65/66과 같은 패턴 — 테스트에서 시간 고정용. 안 주면 `datetime.now(timezone.utc)`.
- **client 인터페이스**: `.select().eq().execute()`, `.update(dict).eq().execute()`, `.upsert(rows, on_conflict=...).execute()` — SUU-65/66과 동일한 supabase-py 모양. 테스트의 FakeClient가 흉내낸다.
- **참고(무관한 이슈)**: 저장소 루트의 `tmp/pytest-suu66-full`, `tmp/pytest-suu66-target` 폴더가 권한 문제로 삭제/열람이 안 돼서 `pytest` 전체 실행이 막힌다. 이 티켓과 무관하니 `pytest -k <모듈이름>` 또는 `--ignore=tmp`로 피해서 테스트하면 된다. 사람이 따로 정리할 것.
