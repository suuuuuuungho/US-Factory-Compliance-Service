"""Build Claude request payloads for eCFR contextual retrieval."""


def build_context_request(
    doc_text: str,
    chunk_text: str,
    *,
    prompt_version: str = "ctx_prompt_v1",
) -> dict:
    """Return the cached document and chunk-specific contextualization prompt."""
    instruction = f"""Write a concise 2-3 sentence English context for the eCFR chunk below.
State which Subpart it belongs to and the industry or emission source that Subpart regulates. Explain whether the chunk covers applicability, definitions, emission limits, test methods, monitoring, recordkeeping and reporting, exceptions, or deadlines, and identify any equipment, materials, or numeric conditions it mentions.
Do not decide whether the regulation applies, invent numbers absent from the source, or compare this text with another Subpart.

<chunk>
{chunk_text}
</chunk>"""

    return {
        "system": [
            {
                "type": "text",
                "text": doc_text,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [{"role": "user", "content": instruction}],
        "prompt_version": prompt_version,
    }
