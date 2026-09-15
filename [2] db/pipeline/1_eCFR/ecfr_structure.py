"""Find an eCFR part and summarize the node types below it.

The eCFR structure endpoint represents a title as a tree.  This module only
handles that in-memory tree; fetching the structure is kept in the following
pipeline step.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


def find_part(structure: dict[str, Any], part: str = "63") -> dict[str, Any]:
    """Return the first ``part`` node whose identifier matches ``part``.

    A part can sit below title, chapter, and subchapter nodes, so the complete
    tree is searched rather than assuming a fixed depth.
    """

    nodes = [structure]
    while nodes:
        node = nodes.pop()
        if node.get("type") == "part" and node.get("identifier") == part:
            return node

        children = node.get("children", [])
        if isinstance(children, list):
            nodes.extend(child for child in children if isinstance(child, dict))

    raise ValueError(f"Part {part} is missing from the eCFR structure")


def count_by_type(node: dict[str, Any]) -> dict[str, int]:
    """Count every descendant of ``node`` by eCFR node type.

    The supplied node itself is excluded.  Reserved nodes are deliberately
    included because they remain part of the published eCFR structure.
    """

    counts: Counter[str] = Counter()
    nodes = node.get("children", [])
    if not isinstance(nodes, list):
        return dict(counts)

    pending = [child for child in nodes if isinstance(child, dict)]
    while pending:
        child = pending.pop()
        node_type = child.get("type")
        if isinstance(node_type, str):
            counts[node_type] += 1

        children = child.get("children", [])
        if isinstance(children, list):
            pending.extend(item for item in children if isinstance(item, dict))

    return dict(counts)


__all__ = ["count_by_type", "find_part"]
