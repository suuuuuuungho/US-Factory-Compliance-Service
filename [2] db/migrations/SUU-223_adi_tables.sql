-- SUU-223: ADI + CAA Dashboard 전용 테이블 9개.
-- 계획 문서: [1] docs/2) db/4_ADI+CAA 구축 계획.md 3-5절 "테이블 스키마"
-- 열 이름은 SUU-221 파서가 만들 parsed/{as_of}/adi_*.jsonl 키의 원본이다. 정책 없이 RLS만 켠다 (SUU-63 패턴).
-- Dashboard 회신도 별도 표 없이 source_system = 'caa_dashboard' 로 같은 표에 들어간다.

create table adi_source_entry (
    release_id uuid not null references common_dataset_release(release_id),
    source_system text not null,                     -- adi / caa_dashboard
    source_key text not null,                        -- ADI: control_number. Dashboard: 행 내용으로 만든 결정적 키
    control_number text,                             -- 문자열 그대로. Dashboard 는 NULL
    facility_name text,
    title text,
    categories jsonb not null,                       -- ['MACT', 'NESHAP'] . Dashboard 는 []
    office text,
    author text,
    recipient text,
    letter_date_raw text,                            -- '04/08/2020' 원본 문자열. 정규화 날짜는 adi_document_version.signed_on
    link_text text,                                  -- Dashboard 'Link to Responses' 표시문구. 날짜 열이 아니다
    affected_subpart_raw text,                       -- Dashboard 'Affected Subpart' 원본 문자열
    abstract text,
    source_url text,
    canonical_url text,                              -- Safe Links 를 벗긴 실제 EPA 주소. 없으면 NULL
    list_sha256 text not null,                       -- 목록 원본 파일 sha256
    source_object_id uuid references common_raw_object(object_id),   -- 목록 원본 (적재기가 채움)
    scope_status text not null,                      -- part63_candidate / out_of_scope / text_missing
    primary key (release_id, source_system, source_key),
    check (source_system in ('adi', 'caa_dashboard'))
);

create table adi_document (
    document_id uuid primary key,                    -- uuid5(sha256)
    canonical_identity text not null unique,         -- 'sha256:{sha256}'. 스캔본·재입력본은 검토 후 adi_document_relation 으로 잇는다
    created_at timestamptz not null default now()
);

create table adi_document_version (
    version_id uuid primary key,                     -- uuid5(sha256 + parser_version)
    document_id uuid not null references adi_document(document_id),
    object_id uuid references common_raw_object(object_id),          -- 회신 파일 원본 (적재기가 채움)
    sha256 text not null,
    signed_on date,                                  -- 본문 확인 전에는 NULL. 임의 날짜로 바꾸지 않는다
    signed_on_raw text,
    date_source text,                                -- adi_list / body / ...
    text_content text,
    extraction_method text not null,                 -- pypdf / ocr / text
    parser_version text not null,
    quality_status text not null,                    -- ok / partial / no_text
    legal_status text not null,                      -- unknown / current / superseded / withdrawn
    unique (document_id, sha256, parser_version)
);

create table adi_entry_document (
    release_id uuid not null,
    source_system text not null,
    source_key text not null,
    version_id uuid not null references adi_document_version(version_id),
    match_method text not null,                      -- fetched_from_entry / hash_match / manual
    match_status text not null,                      -- 검토 전 / 확인됨 / 불명
    primary key (release_id, source_system, source_key, version_id),
    foreign key (release_id, source_system, source_key) references adi_source_entry(release_id, source_system, source_key)
);

create table adi_page (
    version_id uuid not null references adi_document_version(version_id),
    page_no integer not null,
    text_content text not null,
    extraction_method text not null,
    ocr_confidence numeric,                          -- OCR 도구가 점수를 주지 않으면 NULL
    status text not null,                            -- ok / empty / failed
    failure_reason text,
    review_status text not null,
    primary key (version_id, page_no)
);

create table adi_block (
    version_id uuid not null references adi_document_version(version_id),
    block_no integer not null,
    page_no integer,                                 -- 텍스트형 원본은 NULL
    kind text not null,                              -- question / answer / condition / signature / ...
    text_content text not null,
    source_locator text,
    review_status text not null,
    primary key (version_id, block_no)
);

create table adi_cfr_reference (
    reference_id uuid primary key,
    version_id uuid not null references adi_document_version(version_id),
    block_no integer,
    raw_citation text not null,                      -- '40 CFR 63.11607'
    title integer,
    part text,
    subpart text,
    section text,
    paragraph text,
    reference_role text not null,                    -- 질문 대상 / 회신상 적용 / 회신상 비적용 / 정의 인용 / 단순 언급
    evidence_locator text,
    review_status text not null,
    historical_ecfr_release_id uuid,                 -- 회신 당시 eCFR. 미확보면 NULL
    historical_node_key text,
    current_ecfr_release_id uuid,
    current_node_key text,
    foreign key (version_id, block_no) references adi_block(version_id, block_no),
    foreign key (historical_ecfr_release_id, historical_node_key) references ecfr_node(release_id, node_key),
    foreign key (current_ecfr_release_id, current_node_key) references ecfr_node(release_id, node_key),
    check ((historical_ecfr_release_id is null) = (historical_node_key is null)),
    check ((current_ecfr_release_id is null) = (current_node_key is null))
);

create table adi_document_relation (
    from_document_id uuid not null references adi_document(document_id),
    to_document_id uuid not null references adi_document(document_id),
    relation_type text not null,                     -- same_document / amends / withdraws / supersedes
    evidence_version_id uuid references adi_document_version(version_id),
    evidence_locator text,
    review_status text not null,
    primary key (from_document_id, to_document_id, relation_type)
);

create table adi_facility_candidate (
    document_id uuid not null references adi_document(document_id),
    echo_release_id uuid not null,
    echo_pgm_sys_id text not null,
    match_evidence text,
    review_status text not null,                     -- 이름만으로 확정하지 않는다. 검토 전 / 확인됨 / 불명
    primary key (document_id, echo_release_id, echo_pgm_sys_id),
    foreign key (echo_release_id, echo_pgm_sys_id) references echo_facility(release_id, pgm_sys_id)
);

create index adi_source_entry_control_number_idx on adi_source_entry (control_number);
create index adi_source_entry_source_key_idx on adi_source_entry (source_system, source_key);
create index adi_source_entry_office_idx on adi_source_entry (office);
create index adi_document_version_document_idx on adi_document_version (document_id);
create index adi_document_version_sha256_idx on adi_document_version (sha256);
create index adi_document_version_signed_on_idx on adi_document_version (signed_on);
create index adi_entry_document_version_idx on adi_entry_document (version_id);
create index adi_block_page_idx on adi_block (version_id, page_no);
create index adi_cfr_reference_version_idx on adi_cfr_reference (version_id);
create index adi_cfr_reference_cfr_idx on adi_cfr_reference (title, part, subpart, section);
create index adi_cfr_reference_current_node_idx on adi_cfr_reference (current_ecfr_release_id, current_node_key);
create index adi_document_relation_to_idx on adi_document_relation (to_document_id);
create index adi_facility_candidate_echo_idx on adi_facility_candidate (echo_release_id, echo_pgm_sys_id);

alter table adi_source_entry enable row level security;
alter table adi_document enable row level security;
alter table adi_document_version enable row level security;
alter table adi_entry_document enable row level security;
alter table adi_page enable row level security;
alter table adi_block enable row level security;
alter table adi_cfr_reference enable row level security;
alter table adi_document_relation enable row level security;
alter table adi_facility_candidate enable row level security;
