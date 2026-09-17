-- SUU-99: rag_chunk 키워드 검색. tsv를 채우고 검색 함수를 만든다.
-- 계획 문서: [1] docs/3) rag/2_rag 구축 계획.md [6] 키워드 검색, [7]-2 후보 모으기
-- 색인 문자열은 임베딩 입력과 같다: context_text + chunk_text

update rag_chunk
set tsv = to_tsvector('english', coalesce(context_text, '') || ' ' || chunk_text)
where tsv is null;

-- 질문의 단어를 OR로 잇는다(BM25처럼 "하나라도 맞으면" 후보). AND(websearch_to_tsquery)는 긴 질문에서 0건이 나온다.
-- ts_rank_cd 정규화 2 = 문서 길이로 나눔. 32문항 비교(0/1/2)에서 Hit@20 17→22, MRR 0.20→0.39로 가장 좋았다.
create or replace function rag_keyword_search(p_release_id uuid, p_query text, p_k int default 150)
returns table (chunk_key text, node_key text, score real)
language sql stable as $$
    select c.chunk_key, c.node_key, ts_rank_cd(c.tsv, q, 2) as score
    from rag_chunk c,
         to_tsquery('english', array_to_string(tsvector_to_array(to_tsvector('english', p_query)), ' | ')) q
    where c.release_id = p_release_id
      and c.index_status = 'embedded'
      and c.tsv @@ q
    order by score desc, c.chunk_key
    limit p_k
$$;
