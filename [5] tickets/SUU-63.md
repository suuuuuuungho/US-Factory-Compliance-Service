# SUU-63 chore(db): 운영 공통 테이블 RLS 켜서 외부 노출 차단

## 목표
SUU-61에서 만든 공통 운영 테이블 8개를 anon/authenticated 롤에서 접근하지 못하게 막는다.

## 건드릴 파일
- 만들 것: `[2] db/migrations/SUU-63_enable_rls_common_tables.sql` — 적용한 DDL 기록
- Claude가 Supabase MCP(`apply_migration`)로 project `husqnrcuoaogdkbpjnep`에 직접 적용함. Codex 작업 아님

## 안 하는 것
- 세부 접근 정책 설계 (지금은 정책 0개 = anon/authenticated 완전 차단이 원하는 상태)

## 완료 기준 ↔ 확인 방법
| 완료 기준 | 확인 방법 |
|---|---|
| get_advisors(security)에서 "RLS 비활성" critical 항목이 사라진다 | 적용 후 재확인, critical 항목 없음 |
| get_advisors(security)에 "정책 없음" info 항목만 남는다 | 8개 테이블 모두 `rls_enabled_no_policy` info로 확인 |

## 적용 결과
- 8개 테이블 모두 `ENABLE ROW LEVEL SECURITY` 적용
- 적용 전: critical advisory `rls_disabled` (8개 테이블, anon/authenticated 전체 노출)
- 적용 후: info advisory `rls_enabled_no_policy` (8개 테이블, 정책 없음 — 의도된 상태)
- `service_role` 키를 쓰는 백엔드 파이프라인은 RLS를 우회하므로 영향 없음. anon/authenticated는 정책이 없어 완전히 막힘.

## Codex 메모
이 티켓은 Codex 작업이 아니다. 나중에 이 테이블들을 프론트엔드에 노출할 계획이 생기면 그때 세부 정책(누가 어떤 행을 볼 수 있는지)을 설계하는 별도 티켓이 필요하다.
