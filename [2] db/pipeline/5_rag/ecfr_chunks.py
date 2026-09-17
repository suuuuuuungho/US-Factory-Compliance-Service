"""Build RAG chunk boundaries from parsed eCFR nodes and blocks."""

MAX_CHUNK_CHARS = 30_000


def _chunk_length(blocks):
    return len("\n\n".join(block["text_content"] for block in blocks))


def _group_at_label_depth(blocks, depth):
    """Group consecutive blocks by one label_path level."""
    groups = []
    current = []
    current_label = None

    for block in blocks:
        label_path = block.get("label_path") or []
        if len(label_path) <= depth:
            current.append(block)
            continue

        label = label_path[depth]
        if not current:
            current = [block]
            current_label = label
        elif current_label is None:
            current.append(block)
            current_label = label
        elif label == current_label:
            current.append(block)
        else:
            groups.append(current)
            current = [block]
            current_label = label

    if current:
        groups.append(current)
    return groups


def _split_body_blocks(blocks, max_chars, depth=0):
    if len(blocks) <= 1 or _chunk_length(blocks) <= max_chars:
        return [blocks]

    groups = _group_at_label_depth(blocks, depth)
    if len(groups) <= 1:
        return [blocks]

    pieces = []
    for group in groups:
        if _chunk_length(group) > max_chars:
            pieces.extend(_split_body_blocks(group, max_chars, depth + 1))
        else:
            pieces.append(group)
    return pieces


def build_chunks(nodes, blocks, *, max_chars=MAX_CHUNK_CHARS):
    """Return body chunks per eligible node and one child per table block."""
    eligible_nodes = [
        node
        for node in nodes
        if node["node_type"] in ("section", "appendix")
        and not node.get("reserved", False)
    ]
    eligible_keys = {node["node_key"] for node in eligible_nodes}
    blocks_by_node = {node_key: [] for node_key in eligible_keys}

    for block in blocks:
        node_key = block["node_key"]
        if node_key in blocks_by_node:
            blocks_by_node[node_key].append(block)

    chunks = []
    for node in eligible_nodes:
        node_key = node["node_key"]
        node_blocks = blocks_by_node[node_key]
        table_blocks = sorted(
            (block for block in node_blocks if block["kind"] == "table"),
            key=lambda block: block["block_no"],
        )
        body_blocks = sorted(
            (block for block in node_blocks if block["kind"] != "table"),
            key=lambda block: block["block_no"],
        )
        base_chunk_key = f"ecfr/{node_key}/0"

        for piece_no, piece in enumerate(_split_body_blocks(body_blocks, max_chars)):
            chunk_key = (
                base_chunk_key
                if piece_no == 0
                else f"{base_chunk_key}-{piece_no}"
            )
            chunks.append({
                "chunk_key": chunk_key,
                "node_key": node_key,
                "block_nos": [block["block_no"] for block in piece],
                "parent_chunk_key": None,
            })

        for sequence, table_block in enumerate(table_blocks, start=1):
            chunks.append({
                "chunk_key": f"ecfr/{node_key}/{sequence}",
                "node_key": node_key,
                "block_nos": [table_block["block_no"]],
                "parent_chunk_key": base_chunk_key,
            })

    return chunks
