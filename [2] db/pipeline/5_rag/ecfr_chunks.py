"""Build RAG chunk boundaries from parsed eCFR nodes and blocks."""


def build_chunks(nodes, blocks):
    """Return one base chunk per eligible node and one child per table block."""
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
        body_block_nos = sorted(
            block["block_no"]
            for block in node_blocks
            if block["kind"] != "table"
        )
        base_chunk_key = f"ecfr/{node_key}/0"

        chunks.append({
            "chunk_key": base_chunk_key,
            "node_key": node_key,
            "block_nos": body_block_nos,
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
