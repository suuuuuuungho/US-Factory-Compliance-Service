"""Build Kanon 2 embedding request payloads for contextualized eCFR chunks."""


def build_embedding_request(context_text: str, chunk_text: str) -> dict:
    """Return the document embedding request for one contextualized chunk."""
    return {
        "texts": [f"{context_text}\n\n{chunk_text}"],
        "task": "retrieval/document",
        "overflow_strategy": None,
    }


__all__ = ["build_embedding_request"]
