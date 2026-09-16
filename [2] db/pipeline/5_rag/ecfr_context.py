"""Build Claude request payloads for eCFR contextual retrieval."""


def build_context_request(
    doc_text: str,
    chunk_text: str,
    *,
    subpart_name: str | None = None,
    prompt_version: str = "ctx_prompt_v1",
) -> dict:
    """Return the cached document and chunk-specific contextualization prompt."""
    subpart_statement = (
        f"This chunk belongs to {subpart_name}.\n" if subpart_name is not None else ""
    )
    instruction = f"""{subpart_statement}Write a concise 2-3 sentence English context for the eCFR chunk below.
State which Subpart it belongs to and the industry or emission source that Subpart regulates. Explain whether the chunk covers applicability, definitions, emission limits, test methods, monitoring, recordkeeping and reporting, exceptions, or deadlines, and identify any equipment, materials, or numeric conditions it mentions.
Do not decide whether the regulation applies, invent numbers absent from the source, or compare this text with another Subpart.
Use every Subpart name exactly as it appears in the source; never invent or substitute a different name.

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
