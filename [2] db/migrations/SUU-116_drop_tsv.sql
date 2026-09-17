-- SUU-116: 키워드 검색을 BM25(파이썬, rank_bm25)로 바꾸면서 ts_rank 흔적을 지운다.
drop function if exists rag_keyword_search(uuid, text, int);
drop index if exists rag_chunk_tsv_gin_idx;
alter table rag_chunk drop column if exists tsv;
