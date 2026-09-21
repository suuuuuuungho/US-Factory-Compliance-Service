-- SUU-208: Federal Register 전용 테이블 4개 (1차: API 메타데이터만).
-- 계획 문서: [1] docs/2) db/db 구축 계획/2_Federal Register 구축 계획.md 3-5절 "테이블 스키마"
-- 열 이름은 SUU-207 파서가 만들 parsed/{as_of}/fr_*.jsonl 키의 원본이다. 정책 없이 RLS만 켠다 (SUU-63 패턴).
-- fr_block · fr_relation · fr_public_inspection 은 본문 파싱 회차에 만든다.

create table fr_document (
    release_id uuid not null references common_dataset_release(release_id),
    document_key text not null,                      -- '{publication_date}/{document_number}' 예: 2026-02-24/2026-03638
    publication_date date not null,
    document_number text not null,                   -- 문자열 그대로. '03-5521' 같은 과거 번호를 바꾸지 않는다
    canonical_url text not null,                     -- html_url
    title text,
    abstract text,
    type_raw text,                                   -- Rule / Proposed Rule / Correction / Uncategorized Document / ...
    action text,
    subtype text,
    agencies jsonb not null,
    citation text,                                   -- '91 FR 9088'
    volume integer,
    start_page integer,
    end_page integer,
    effective_on date,                               -- API 값 그대로. 조항별 시행일은 fr_date_event
    comments_close_on date,
    signing_date date,
    docket_ids jsonb,
    regulation_id_numbers jsonb,
    full_text_xml_url text,
    pdf_url text,
    source_object_id uuid references common_raw_object(object_id),   -- 상세 JSON 원본
    body_object_id uuid references common_raw_object(object_id),     -- XML 원본 (있을 때)
    pdf_object_id uuid references common_raw_object(object_id),      -- PDF 원본 (있을 때)
    content_hash text not null,                      -- 상세 JSON sha256
    raw_metadata jsonb not null,                     -- 상세 JSON 전체
    scope_status text not null,                      -- part63_list / supplement_candidate
    body_status text not null,                       -- xml / pdf_only / missing
    primary key (release_id, document_key),
    unique (release_id, publication_date, document_number)
);

create table fr_identifier (
    release_id uuid not null references common_dataset_release(release_id),
    document_key text not null,
    identifier_kind text not null,                   -- docket / rin
    identifier_value text not null,                  -- 'EPA-HQ-OAR-2018-0794', '2060-AW68'
    primary key (release_id, document_key, identifier_kind, identifier_value),
    foreign key (release_id, document_key) references fr_document(release_id, document_key)
);

create table fr_cfr_reference (
    reference_id uuid primary key,
    release_id uuid not null references common_dataset_release(release_id),
    document_key text not null,
    title integer not null,
    part text,
    subpart text,                                    -- 1차는 NULL (본문 추출 전)
    section text,
    paragraph text,
    relation_type text not null,                     -- affects (API cfr_references) / amends / mentions
    raw_citation text,
    evidence_locator text,
    review_status text not null,                     -- 검토 전 / 확인됨 / 불명
    ecfr_release_id uuid,
    ecfr_node_key text,
    foreign key (release_id, document_key) references fr_document(release_id, document_key),
    foreign key (ecfr_release_id, ecfr_node_key) references ecfr_node(release_id, node_key),
    check ((ecfr_release_id is null) = (ecfr_node_key is null))
);

create table fr_date_event (
    event_id uuid primary key,
    release_id uuid not null references common_dataset_release(release_id),
    document_key text not null,
    event_kind text not null,                        -- effective / comments_close / signing / ...
    event_date date,
    applies_to text,
    raw_text text,
    evidence_locator text,
    review_status text not null,
    foreign key (release_id, document_key) references fr_document(release_id, document_key)
);

create index fr_document_publication_date_idx on fr_document (publication_date);
create index fr_document_document_number_idx on fr_document (document_number);
create index fr_identifier_value_idx on fr_identifier (identifier_kind, identifier_value);
create index fr_cfr_reference_document_idx on fr_cfr_reference (release_id, document_key);
create index fr_cfr_reference_cfr_idx on fr_cfr_reference (title, part, subpart, section);
create index fr_date_event_document_idx on fr_date_event (release_id, document_key);
create index fr_date_event_date_idx on fr_date_event (event_kind, event_date);

alter table fr_document enable row level security;
alter table fr_identifier enable row level security;
alter table fr_cfr_reference enable row level security;
alter table fr_date_event enable row level security;
