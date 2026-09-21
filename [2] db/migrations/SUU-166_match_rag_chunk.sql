-- SUU-166: 질문 벡터와 가까운 청크 k개. 서버가 임베딩을 안 들고 있으려고 DB에서 계산한다.
-- 5,625행이라 인덱스 없이 정확 계산(수십 ms). score = 코사인 유사도 = 1 - 거리. ecfr_index_run.rank_chunks_by_similarity와 같은 값.

create or replace function match_rag_chunk(query_embedding vector(1792), p_release_id uuid, k integer)
returns table (chunk_key text, score double precision)
language sql stable
as $$
    select chunk_key, 1 - (embedding <=> query_embedding) as score
    from rag_chunk
    where release_id = p_release_id and index_status = 'embedded'
    order by embedding <=> query_embedding
    limit k
$$;
