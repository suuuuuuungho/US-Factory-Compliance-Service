"""SUU-166: search_sections(vector=...)를 주면 메모리 코사인 대신 그 함수(pgvector RPC)가 고른 청크로 검색한다.
안 주면 지금처럼 메모리 계산. 네트워크는 쓰지 않는다.
"""
from ecfr_index_run import rank_chunks_by_similarity
from ecfr_search import search_sections


def chunk(chunk_key, embedding=None):
    node_key = chunk_key.removeprefix("ecfr/").rsplit("/", 1)[0]
    c = {"chunk_key": chunk_key, "node_key": node_key, "chunk_text": f"text of {chunk_key}"}
    if embedding is not None:
        c["embedding"] = embedding
    return c


KEYS = [
    "ecfr/40/63/subpart-A/section-63.6/0",
    "ecfr/40/63/subpart-PPPP/section-63.4481/1",
    "ecfr/40/63/subpart-A/section-63.2/0",
    "ecfr/40/63/subpart-PPPP/section-63.4481/0",
]
EMBEDDINGS = [[0.0, 1.0], [1.0, 1.0], [0.5, 1.0], [1.0, 0.0]]
QUESTION = "Does Subpart PPPP cover solvent welding?"


def fake_embed(request):
    return [1.0, 0.0]


def test_vector_replaces_memory_cosine_and_needs_no_embeddings():
    # 색인에 embedding이 없다. vector()가 점수 붙은 청크를 돌려주면 그걸로 검색한다
    chunks = [chunk(k) for k in KEYS]
    by_key = {c["chunk_key"]: c for c in chunks}
    calls = []

    def vector(query_embedding, k):
        calls.append((query_embedding, k))
        return [{**by_key[KEYS[3]], "score": 1.0}, {**by_key[KEYS[1]], "score": 0.7}, {**by_key[KEYS[2]], "score": 0.4}]

    hits = search_sections(QUESTION, embed=fake_embed, chunks=chunks, vector=vector, chunk_top_k=3, top_k=2)
    assert calls == [([1.0, 0.0], 3)]
    assert [h["section_key"] for h in hits] == ["section-63.4481", "section-63.2"]
    assert hits[0]["chunk_key"] == KEYS[3] and hits[0]["score"] == 1.0


def test_vector_path_matches_memory_path_when_scores_agree():
    with_embeddings = [chunk(k, e) for k, e in zip(KEYS, EMBEDDINGS)]
    memory = search_sections(QUESTION, embed=fake_embed, chunks=with_embeddings, chunk_top_k=3, top_k=3)

    # vector()가 메모리 코사인과 같은 순서·점수를 주면 결과가 똑같다
    def vector(query_embedding, k):
        return rank_chunks_by_similarity(query_embedding, with_embeddings, top_k=k)

    assert search_sections(QUESTION, embed=fake_embed, chunks=with_embeddings, vector=vector, chunk_top_k=3, top_k=3) == memory


def test_vector_hits_go_through_rrf_with_keyword_and_rerank():
    chunks = [chunk(k) for k in KEYS]
    by_key = {c["chunk_key"]: c for c in chunks}
    seen = []

    def vector(query_embedding, k):
        return [{**by_key[KEYS[3]], "score": 1.0}, {**by_key[KEYS[0]], "score": 0.5}]

    def keyword(question, k):
        return [{"chunk_key": KEYS[0], "node_key": chunks[0]["node_key"], "score": 0.9},
                {"chunk_key": KEYS[3], "node_key": chunks[3]["node_key"], "score": 0.8}]

    def rerank(question, ranked):
        seen.append([c["chunk_key"] for c in ranked])
        return [0.0] * len(ranked)

    search_sections(QUESTION, embed=fake_embed, chunks=chunks, vector=vector, keyword=keyword, rerank=rerank, chunk_top_k=2)
    # 두 목록 다 1·2등이라 RRF 동점 → chunk_key 사전순
    assert seen == [[KEYS[0], KEYS[3]]]
