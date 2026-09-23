# SUU-64 feat(db): eCFR 전용 테이블을 Supabase에 만든다

## 목표
ecfr_node 등 eCFR 전용 테이블 6개를 Supabase에 만들고 RLS로 외부 노출을 막는다.

## 건드릴 파일
- 만들 것: `[2] db/migrations/SUU-64_ecfr_tables.sql` — 적용한 DDL 기록
- Claude가 Supabase MCP(`apply_migration`)로 project `husqnrcuoaogdkbpjnep`에 직접 적용함. Codex 작업 아님

## 안 하는 것
- 실제 데이터 적재 (다음 티켓 — nodes.jsonl 등을 이 테이블에 넣는 loader)
- 세부 RLS 접근 정책 (SUU-63과 같은 이유로 정책 없이 RLS만 켠다 — service_role만 접근, anon/authenticated 차단)

## 완료 기준 ↔ 확인 방법
| 완료 기준 | 확인 방법 |
|---|---|
| list_tables로 6개 테이블이 모두 보인다 | `list_tables` 결과로 확인 완료 |
| ecfr_node의 PK가 (release_id, node_key)다 | 마이그레이션의 `primary key (release_id, node_key)` 그대로 적용, 확인 완료 |
| ecfr_block의 PK가 (release_id, node_key, block_no)이고 ecfr_node에 FK로 연결된다 | 마이그레이션의 PK + `foreign key (release_id, node_key) references ecfr_node` 적용, 확인 완료 |

## 적용 결과
- 6개 테이블 모두 생성: ecfr_node, ecfr_block, ecfr_reference, ecfr_asset, ecfr_history, ecfr_correction
- 계획 문서 그대로 복합 PK·FK 연결 (node→block→reference/asset, node의 자기참조 parent_key, history/correction→common_raw_object)
- Supabase 보안 advisory(critical, RLS 비활성)가 이번에는 SUU-61/63 패턴을 미리 적용해 같은 마이그레이션 안에서 즉시 해결함(정책 없이 RLS만 켬 — service_role만 접근 가능, anon/authenticated 차단)

## Codex 메모
이 티켓은 Codex 작업이 아니다. 다음 티켓(nodes.jsonl → ecfr_node 등 loader)에서 Codex가 작성하는 Python 코드는 이 6개 테이블이 이미 있다는 것을 전제로 짤 수 있다.
