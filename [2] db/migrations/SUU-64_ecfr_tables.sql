-- SUU-64: eCFR 전용 테이블.
-- 계획 문서: [1] docs/2) db/1_eCFR 구축 계획.md 3-5절(두 번째) "테이블 스키마 — eCFR 전용"

create table ecfr_node (
    release_id uuid not null references common_dataset_release(release_id),
    node_key text not null,
    parent_key text,
    node_type text not null,
    identifier text,
    heading text,
    reserved boolean not null default false,
    sort_order integer not null,
    source_object_id uuid not null references common_raw_object(object_id),
    source_locator text,
    xml_fragment text,
    content_hash text,
    primary key (release_id, node_key),
    foreign key (release_id, parent_key) references ecfr_node(release_id, node_key)
);

create table ecfr_block (
    release_id uuid not null,
    node_key text not null,
    block_no integer not null,
    kind text not null,
    label_path text[],
    text_content text,
    markup text,
    source_locator text,
    parse_status text not null,
    primary key (release_id, node_key, block_no),
    foreign key (release_id, node_key) references ecfr_node(release_id, node_key)
);

create table ecfr_reference (
    reference_id uuid primary key,
    release_id uuid not null,
    node_key text not null,
    block_no integer not null,
    raw_citation text not null,
    target_title integer,
    target_part text,
    target_subpart text,
    target_section text,
    target_paragraph text,
    target_node_key text,
    resolution_status text not null,
    evidence_locator text,
    foreign key (release_id, node_key, block_no) references ecfr_block(release_id, node_key, block_no)
);

create table ecfr_asset (
    release_id uuid not null,
    node_key text not null,
    block_no integer not null,
    asset_no integer not null,
    source_url text not null,
    object_id uuid references common_raw_object(object_id),
    fetch_status text not null,
    primary key (release_id, node_key, block_no, asset_no),
    foreign key (release_id, node_key, block_no) references ecfr_block(release_id, node_key, block_no)
);

create table ecfr_history (
    history_key text primary key,
    source_object_id uuid not null references common_raw_object(object_id),
    identifier text,
    type text,
    title text,
    part text,
    subpart text,
    date date,
    amendment_date date,
    issue_date date,
    substantive boolean,
    removed boolean,
    raw_metadata jsonb
);

create table ecfr_correction (
    correction_id text primary key,
    source_object_id uuid not null references common_raw_object(object_id),
    cfr_references jsonb,
    corrective_action text,
    error_occurred date,
    error_corrected date,
    last_modified date,
    fr_citation text,
    raw_metadata jsonb
);
