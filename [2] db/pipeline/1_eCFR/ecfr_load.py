"""Load parsed eCFR nodes and blocks into their release tables."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ecfr_parse import PARSER_VERSION


NODE_COLUMNS = (
    "node_key",
    "parent_key",
    "node_type",
    "identifier",
    "heading",
    "reserved",
    "sort_order",
    "source_locator",
    "xml_fragment",
    "content_hash",
)
BLOCK_COLUMNS = (
    "node_key",
    "block_no",
    "kind",
    "label_path",
    "text_content",
    "markup",
    "source_locator",
    "parse_status",
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_release(
    root: Path,
    as_of: str,
    release_id: str,
    *,
    client: Any,
) -> None:
    """Load one parsed eCFR release into ``ecfr_node`` and ``ecfr_block``."""

    parsed_dir = Path(root) / "parsed" / as_of / PARSER_VERSION
    nodes = _read_jsonl(parsed_dir / "nodes.jsonl")
    blocks = _read_jsonl(parsed_dir / "blocks.jsonl")

    release_objects = (
        client.table("common_release_object")
        .select("object_id")
        .eq("release_id", release_id)
        .eq("role", "xml")
        .execute()
        .data
    )
    source_object_id = release_objects[0]["object_id"]

    node_rows = [
        {
            **{column: node[column] for column in NODE_COLUMNS},
            "release_id": release_id,
            "source_object_id": source_object_id,
        }
        for node in nodes
    ]
    block_rows = [
        {
            **{column: block[column] for column in BLOCK_COLUMNS},
            "release_id": release_id,
        }
        for block in blocks
    ]

    client.table("ecfr_node").upsert(
        node_rows,
        on_conflict="release_id,node_key",
    ).execute()
    client.table("ecfr_block").upsert(
        block_rows,
        on_conflict="release_id,node_key,block_no",
    ).execute()


__all__ = ["load_release"]
