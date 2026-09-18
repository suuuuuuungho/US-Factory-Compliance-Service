"""SUU-131: 로컬 리랭커(bge / nemotron)는 Kanon과 같은 입력을 받아 같은 모양의 점수를 돌려준다."""
import pytest

from ecfr_rerank_local import build_local_reranker, rerank_pairs
from ecfr_search import build_rerank_request

CHUNKS = [
    {"chunk_key": "a", "context_text": "ctx a", "chunk_text": "body a"},
    {"chunk_key": "b", "context_text": "", "chunk_text": "body b"},
    {"chunk_key": "c", "context_text": "ctx c", "chunk_text": "body c"},
]


def test_local_pairs_match_kanon_texts():
    pairs = rerank_pairs("q", CHUNKS)
    assert [p[0] for p in pairs] == ["q", "q", "q"]
    assert [p[1] for p in pairs] == build_rerank_request("q", CHUNKS)["texts"]


def test_local_rerank_returns_score_per_chunk():
    calls = []

    def score_batch(pairs):  # 모델 대신: 본문 길이를 점수로
        calls.append(len(pairs))
        return [float(len(p[1])) for p in pairs]

    rerank = build_local_reranker(score_batch, batch_size=2)
    scores = rerank("q", CHUNKS)
    assert scores == [len("ctx a\n\nbody a"), len("body b"), len("ctx c\n\nbody c")]
    assert calls == [2, 1]


def test_unknown_reranker_raises():
    from ecfr_rerank_local import load_scorer
    with pytest.raises(ValueError):
        load_scorer("nope")
