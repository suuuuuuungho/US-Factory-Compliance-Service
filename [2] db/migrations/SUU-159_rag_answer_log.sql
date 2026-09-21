-- SUU-159: 서비스 질문 로그. /ask 한 번에 한 줄. 정책 없이 RLS만 켠다 (SUU-63 패턴).
-- 계획 문서: [1] docs/3) rag/2_rag 구축 계획.md [8]절

create table rag_answer_log (
    id bigint generated always as identity primary key,
    created_at timestamptz not null default now(),
    release_id uuid not null references common_dataset_release(release_id),
    question text not null,
    answer jsonb,
    sections jsonb not null,
    issues jsonb not null,
    prompt_tokens integer not null,
    completion_tokens integer not null,
    cost_usd numeric(10, 6) not null,
    ms integer not null
);

alter table rag_answer_log enable row level security;
