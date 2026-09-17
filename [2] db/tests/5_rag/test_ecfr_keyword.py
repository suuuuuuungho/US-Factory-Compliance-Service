"""SUU-116: 키워드 검색은 BM25다. 청크는 메모리에서 색인하고, keyword(question, k)로 끼운다."""
from ecfr_keyword import build_keyword_search, tokenize


def chunk(key, context, text):
    return {"chunk_key": f"ecfr/{key}/0", "node_key": key, "context_text": context, "chunk_text": text}


COMMON = "This section applies to each affected source at a major source of hazardous air pollutants."
CHUNKS = [
    chunk("a", "Applicability of Subpart X.", COMMON + " The boiler must meet the emission limit."),
    chunk("b", "Recordkeeping for Subpart Y.", COMMON + " The facility must keep records of each source."),
    chunk("c", "Test methods for Subpart Z.", "Sample the stack for chromium each year."),
    chunk("d", "Definitions for Subpart Y.", "Terms used in this subpart are defined here."),
    chunk("e", "Reporting for Subpart Z.", "Submit the compliance report every six months."),
]


def test_tokenize_lowercases_and_keeps_section_numbers():
    assert tokenize("Boiler MACT, see 63.7485(a).") == ["boiler", "mact", "see", "63.7485", "a"]


def test_rare_word_outranks_common_words():
    keyword = build_keyword_search(CHUNKS)
    hits = keyword("Does our boiler have to meet the emission limit at the source?", 3)
    assert hits[0]["node_key"] == "a"


def test_hits_have_keys_and_descend_by_score():
    keyword = build_keyword_search(CHUNKS)
    hits = keyword("chromium at the source", 2)
    assert len(hits) == 2
    assert set(hits[0]) == {"chunk_key", "node_key", "score"}
    assert hits[0]["score"] >= hits[1]["score"]
    assert hits[0]["node_key"] == "c"


def test_context_text_is_indexed_too():
    keyword = build_keyword_search(CHUNKS)
    assert keyword("recordkeeping", 1)[0]["node_key"] == "b"


def test_query_with_no_overlap_returns_nothing():
    keyword = build_keyword_search(CHUNKS)
    assert keyword("zzz qqq", 3) == []
