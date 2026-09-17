"""SUU-130: rrf_merge(weights=...) — 목록별 가중치. 없으면 예전과 같다."""
from ecfr_search import rrf_merge


def _chunk(key):
    return {"chunk_key": key, "node_key": f"ecfr/subpart-A/section-63.{key}", "score": 1.0}


A = [_chunk("1"), _chunk("2"), _chunk("3")]
B = [_chunk("3"), _chunk("4"), _chunk("1")]


def test_rrf_merge_default_unchanged():
    assert [c["chunk_key"] for c in rrf_merge([A, B])] == [c["chunk_key"] for c in rrf_merge([A, B], weights=[1.0, 1.0])]
    assert [c["chunk_key"] for c in rrf_merge([A, B])] == ["1", "3", "2", "4"]


def test_rrf_merge_zero_weight_ignores_list():
    only_a = rrf_merge([A], k=60)
    merged = rrf_merge([A, B], k=60, weights=[1.0, 0.0])
    assert [(c["chunk_key"], c["score"]) for c in merged] == [(c["chunk_key"], c["score"]) for c in only_a]


def test_rrf_merge_weight_scales_score():
    merged = rrf_merge([A, B], k=60, weights=[0.25, 0.75])
    by_key = {c["chunk_key"]: c["score"] for c in merged}
    assert by_key["2"] == 0.25 / 62 and by_key["4"] == 0.75 / 62
    assert [c["chunk_key"] for c in merged][:2] == ["3", "1"]  # B 쪽이 무거우면 B 1등(3)이 앞
