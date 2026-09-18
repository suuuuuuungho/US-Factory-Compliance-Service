"""SUU-133: 로컬 임베더(bge-m3)로 청크 본문(컨텍스트 유/무)을 임베딩한다."""
from ecfr_embed_local import build_local_embedder, chunk_document_text


def test_local_embed_returns_unit_vectors():
    def encode(texts):  # 모델 대신: 길이·개수로 정규화 안 된 벡터
        return [[float(len(t)), 1.0, 0.0] for t in texts]

    embed = build_local_embedder(encode, batch_size=2)
    vectors = embed(["a", "bb", "ccc"])
    assert len(vectors) == 3
    for v in vectors:
        assert abs(sum(x * x for x in v) - 1.0) < 1e-6


def test_no_context_uses_chunk_text_only():
    chunk = {"context_text": "ctx", "chunk_text": "body"}
    assert chunk_document_text(chunk, with_context=False) == "body"
    assert chunk_document_text(chunk, with_context=True) == "ctx\n\nbody"
    assert chunk_document_text({"context_text": "", "chunk_text": "body"}, with_context=True) == "body"
