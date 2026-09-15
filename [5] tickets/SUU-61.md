# SUU-61 feat(db): eCFR 운영 공통 테이블을 Supabase에 만든다

## 목표
common_ingest_run 등 4개 데이터셋이 같이 쓰는 운영 테이블 8개를 Supabase에 만든다.

## 건드릴 파일
- 만들 것: `[2] db/migrations/SUU-61_common_tables.sql` — 적용한 DDL 기록 (일회성 마이그레이션, 2_rules.md 9번 예외)
- Claude가 Supabase MCP(`apply_migration`)로 project `husqnrcuoaogdkbpjnep`에 직접 적용함. Codex 작업 아님

## 안 하는 것
- ecfr_* 전용 테이블 (다음 티켓)
- 실제 데이터 적재
- RLS 정책 (아래 "적용 결과" 참고 — 정책 없이 켜면 전체 접근이 막히므로 별도 티켓에서 다룬다)

## 완료 기준 ↔ 확인 방법
| 완료 기준 | 확인 방법 |
|---|---|
| list_tables로 8개 테이블이 모두 보인다 | `list_tables` 실행 결과로 확인 완료 |
| common_dataset_release에 (dataset, scope_key, manifest_hash, parser_version) 고유 제약이 있다 | 마이그레이션의 `unique (...)` 그대로 적용, `list_tables` verbose로 확인 |
| common_raw_object에 (source_url, sha256) 고유 제약이 있다 | 마이그레이션의 `unique (source_url, sha256)` 그대로 적용, `list_tables` verbose로 확인 |

## 적용 결과
- 8개 테이블 모두 생성 확인: common_ingest_run, common_raw_object, common_dataset_release, common_dataset_current, common_release_object, common_ingest_checkpoint, common_ingest_error, common_change_log
- 외래키·기본키·고유 제약 모두 계획 문서(3-5절)대로 걸림
- Supabase 보안 advisory: 8개 테이블 모두 RLS 비활성 상태. 지금은 이 프로젝트에 anon key를 쓰는 클라이언트가 없어 당장 위험하지 않지만, 프론트엔드가 붙기 전에 RLS 정책을 반드시 설계해야 한다. 이 티켓에서는 정책 없이 RLS만 켜면 전체 접근이 막히므로 켜지 않았다.

## Codex 메모
이 티켓은 Codex 작업이 아니다. 다음 이어지는 티켓(ecfr_* 전용 테이블, 실제 loader)에서 Codex가 작성하는 Python 코드는 이 8개 테이블이 이미 있다는 것을 전제로 짤 수 있다.
