-- SUU-121: ECHO 전용 테이블 14개 (파서 산출 13개 + echo_code_map).
-- 계획 문서: [1] docs/2) db/3_ECHO 구축 계획.md 3-5절 "테이블 스키마"
-- 열 이름은 parsed/{as_of}/*.jsonl 키와 같다 (SUU-111/112). 정책 없이 RLS만 켠다 (SUU-63 패턴).

create table echo_source_row (
    release_id uuid not null references common_dataset_release(release_id),
    source_file text not null,
    source_row_no bigint not null,
    raw_payload jsonb not null,
    row_hash text not null,
    parse_status text not null,
    error text,
    source_object_id uuid references common_raw_object(object_id),
    primary key (release_id, source_file, source_row_no)
);

create table echo_facility (
    release_id uuid not null references common_dataset_release(release_id),
    pgm_sys_id text not null,
    registry_id text,
    name text,
    address text,
    city text,
    county text,
    state text,
    zip text,
    epa_region text,
    facility_type text,
    source_class text,
    source_class_desc text,
    operating_status text,
    operating_status_desc text,
    current_hpv text,
    local_control_region_code text,
    local_control_region_name text,
    primary key (release_id, pgm_sys_id)
);

create table echo_facility_identifier (
    release_id uuid not null references common_dataset_release(release_id),
    program_system text not null,
    pgm_sys_id text not null,
    registry_id text not null,
    mapping_source text not null,
    review_status text not null,
    primary key (release_id, program_system, pgm_sys_id, registry_id),
    foreign key (release_id, pgm_sys_id) references echo_facility(release_id, pgm_sys_id)
);

create table echo_industry (
    release_id uuid not null,
    pgm_sys_id text not null,
    code_system text not null,
    code text not null,
    source_locator text,
    primary key (release_id, pgm_sys_id, code_system, code),
    foreign key (release_id, pgm_sys_id) references echo_facility(release_id, pgm_sys_id)
);

create table echo_program (
    release_id uuid not null,
    pgm_sys_id text not null,
    program_code text not null,
    description text,
    status_code text,
    status_desc text,
    begin_date date,
    updated_date date,
    raw_dates jsonb,
    primary key (release_id, pgm_sys_id, program_code),
    foreign key (release_id, pgm_sys_id) references echo_facility(release_id, pgm_sys_id)
);

create table echo_program_subpart (
    release_id uuid not null,
    pgm_sys_id text not null,
    program_code text not null,
    subpart_code text not null,
    subpart_desc text,
    cfr_title integer,
    cfr_part text,
    cfr_subpart text,
    mapping_status text not null,
    primary key (release_id, pgm_sys_id, program_code, subpart_code),
    foreign key (release_id, pgm_sys_id, program_code) references echo_program(release_id, pgm_sys_id, program_code)
);

create table echo_pollutant (
    release_id uuid not null,
    pgm_sys_id text not null,
    pollutant_key text not null,
    pollutant_code text,
    description text,
    srs_id text,
    cas_number text,
    class_code text,
    class_desc text,
    source_locator text,
    review_status text not null,
    primary key (release_id, pgm_sys_id, pollutant_key),
    foreign key (release_id, pgm_sys_id) references echo_facility(release_id, pgm_sys_id)
);

create table echo_activity (
    release_id uuid not null references common_dataset_release(release_id),
    activity_kind text not null,
    activity_id text not null,
    type_code text,
    type_desc text,
    lead_flag text,
    monitor_code text,
    monitor_desc text,
    activity_date date,
    raw_date text,
    attributes jsonb,
    primary key (release_id, activity_kind, activity_id),
    check (activity_kind in ('inspection', 'stack_test', 'titlev', 'formal', 'informal'))
);

create table echo_activity_facility (
    release_id uuid not null,
    activity_kind text not null,
    activity_id text not null,
    pgm_sys_id text not null,
    primary key (release_id, activity_kind, activity_id, pgm_sys_id),
    foreign key (release_id, activity_kind, activity_id) references echo_activity(release_id, activity_kind, activity_id),
    foreign key (release_id, pgm_sys_id) references echo_facility(release_id, pgm_sys_id)
);

create table echo_violation (
    release_id uuid not null references common_dataset_release(release_id),
    violation_id text not null,
    determination_uid text,
    policy_code text,
    agency text,
    state text,
    first_frv_date date,
    hpv_dayzero_date date,
    resolved_date date,
    programs jsonb,
    pollutants jsonb,
    raw_dates jsonb,
    attributes jsonb,
    primary key (release_id, violation_id)
);

create table echo_violation_facility (
    release_id uuid not null,
    violation_id text not null,
    pgm_sys_id text not null,
    primary key (release_id, violation_id, pgm_sys_id),
    foreign key (release_id, violation_id) references echo_violation(release_id, violation_id),
    foreign key (release_id, pgm_sys_id) references echo_facility(release_id, pgm_sys_id)
);

create table echo_penalty (
    release_id uuid not null,
    penalty_key text not null,
    activity_kind text not null,
    activity_id text not null,
    amount numeric,
    amount_kind text not null,
    currency text not null,
    amount_scope text not null,
    raw_amount text,
    source_locator text,
    primary key (release_id, penalty_key),
    foreign key (release_id, activity_kind, activity_id) references echo_activity(release_id, activity_kind, activity_id)
);

create table echo_pipeline_link (
    release_id uuid not null references common_dataset_release(release_id),
    link_key text not null,
    pgm_sys_id text not null,
    eval_activity_id text,
    violation_activity_id text,
    ea_activity_id text,
    ea_fea_activity_id text,
    flags jsonb not null,
    synthetic_violation boolean not null,
    resolution_status text not null,
    resolved_eval_kind text,
    resolved_eval_id text,
    resolved_violation_id text,
    resolved_ea_kind text,
    resolved_ea_id text,
    source_row_no bigint not null,
    attributes jsonb,
    primary key (release_id, link_key),
    foreign key (release_id, resolved_eval_kind, resolved_eval_id) references echo_activity(release_id, activity_kind, activity_id),
    foreign key (release_id, resolved_ea_kind, resolved_ea_id) references echo_activity(release_id, activity_kind, activity_id),
    foreign key (release_id, resolved_violation_id) references echo_violation(release_id, violation_id),
    check ((resolved_eval_kind is null) = (resolved_eval_id is null)),
    check ((resolved_ea_kind is null) = (resolved_ea_id is null))
);

create table echo_code_map (
    dictionary_version text not null,
    program_code text not null,
    raw_subpart_code text not null,
    raw_description text not null,
    cfr_title integer,
    cfr_part text,
    cfr_subpart text,
    source_url text not null,
    review_status text not null,
    primary key (dictionary_version, program_code, raw_subpart_code, raw_description)
);

alter table echo_source_row enable row level security;
alter table echo_facility enable row level security;
alter table echo_facility_identifier enable row level security;
alter table echo_industry enable row level security;
alter table echo_program enable row level security;
alter table echo_program_subpart enable row level security;
alter table echo_pollutant enable row level security;
alter table echo_activity enable row level security;
alter table echo_activity_facility enable row level security;
alter table echo_violation enable row level security;
alter table echo_violation_facility enable row level security;
alter table echo_penalty enable row level security;
alter table echo_pipeline_link enable row level security;
alter table echo_code_map enable row level security;
