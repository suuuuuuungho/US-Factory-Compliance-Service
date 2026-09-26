-- SUU-61: 4개 데이터셋(eCFR/FR/ECHO/ADI+CAA)이 공유하는 운영 테이블.
-- 계획 문서: [1] docs/2) db/1_eCFR 구축 계획.md 3-5절 "테이블 스키마 — 네 데이터셋 공통"

create table common_ingest_run (
    run_id uuid primary key,
    dataset text not null,
    scope jsonb,
    status text not null,
    started_at timestamptz not null,
    finished_at timestamptz,
    counts jsonb,
    error_summary text
);

create table common_raw_object (
    object_id uuid primary key,
    run_id uuid not null references common_ingest_run(run_id),
    source_url text not null,
    final_url text,
    storage_uri text,
    sha256 text not null,
    byte_size bigint,
    media_type text,
    fetched_at timestamptz not null,
    source_modified_at timestamptz,
    etag text,
    unique (source_url, sha256)
);

create table common_dataset_release (
    release_id uuid primary key,
    dataset text not null,
    scope_key text not null,
    run_id uuid not null references common_ingest_run(run_id),
    source_as_of date,
    manifest_hash text not null,
    parser_version text not null,
    status text not null,
    published_at timestamptz,
    unique (dataset, scope_key, manifest_hash, parser_version)
);

create table common_dataset_current (
    dataset text not null,
    scope_key text not null,
    release_id uuid not null references common_dataset_release(release_id),
    last_checked_at timestamptz not null,
    latest_source_as_of date,
    primary key (dataset, scope_key)
);

create table common_release_object (
    release_id uuid not null references common_dataset_release(release_id),
    object_id uuid not null references common_raw_object(object_id),
    role text not null,
    primary key (release_id, object_id)
);

create table common_ingest_checkpoint (
    dataset text not null,
    scope_key text not null,
    partition_key text not null,
    cursor jsonb,
    completed_run_id uuid references common_ingest_run(run_id),
    completed_at timestamptz,
    primary key (dataset, scope_key, partition_key)
);

create table common_ingest_error (
    error_id uuid primary key,
    run_id uuid not null references common_ingest_run(run_id),
    object_id uuid references common_raw_object(object_id),
    record_locator text,
    stage text,
    error_code text,
    message text,
    retryable boolean,
    resolved_at timestamptz
);

create table common_change_log (
    change_id uuid primary key,
    event_key text not null unique,
    run_id uuid not null references common_ingest_run(run_id),
    dataset text not null,
    source_key text not null,
    change_type text not null,
    old_release_id uuid references common_dataset_release(release_id),
    new_release_id uuid not null references common_dataset_release(release_id),
    old_hash text,
    new_hash text,
    detected_at timestamptz not null,
    delivery_status text
);
