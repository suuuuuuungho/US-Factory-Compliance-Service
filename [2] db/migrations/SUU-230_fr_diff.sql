-- SUU-230: Federal Register 규칙별 eCFR 전후 diff (SUU-228 fr_diff.py 결과). 바뀐 문단 + 앞뒤 맥락 1문단만 들어간다.
-- 같은 release 의 fr_document 에 매달린다. 정책 없이 RLS만 켠다 (SUU-63 패턴).

create table fr_diff (
    release_id uuid not null references common_dataset_release(release_id),
    document_key text not null,                      -- fr_document.document_key
    section text not null,                           -- '63.2233'
    node_key text,                                   -- eCFR node_key '40/63/subpart-DDDD/section-63.2233' (없으면 null)
    seq integer not null,                            -- 섹션 안 줄 순서 (1부터)
    change_kind text not null,                       -- equal / changed / removed / added
    before_text text,
    after_text text,
    is_context boolean not null,                     -- true = 안 바뀐 맥락 줄
    before_date date not null,                       -- eCFR 스냅샷 날짜 (시행 전날)
    after_date date not null,                        -- eCFR 스냅샷 날짜 (시행일)
    primary key (release_id, document_key, section, seq),
    foreign key (release_id, document_key) references fr_document(release_id, document_key)
);

create index fr_diff_node_key_idx on fr_diff (node_key);

alter table fr_diff enable row level security;
