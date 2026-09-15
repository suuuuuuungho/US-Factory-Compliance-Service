-- SUU-63: SUU-61에서 만든 공통 운영 테이블 8개를 anon/authenticated 롤에서 차단한다.
-- 정책을 만들지 않는다: service_role은 RLS를 우회하므로 백엔드 파이프라인 접근에는 영향이 없고,
-- anon/authenticated는 정책이 없으므로 완전히 막힌다. 클라이언트 노출 계획이 생기면 그때 정책을 추가한다.

ALTER TABLE "public"."common_ingest_run" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "public"."common_raw_object" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "public"."common_dataset_release" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "public"."common_dataset_current" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "public"."common_release_object" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "public"."common_ingest_checkpoint" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "public"."common_ingest_error" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "public"."common_change_log" ENABLE ROW LEVEL SECURITY;
