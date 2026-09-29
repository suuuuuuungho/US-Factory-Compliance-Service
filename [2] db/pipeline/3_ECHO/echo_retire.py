"""Retire the rows and releases superseded by a newly published ECHO release."""

from typing import Any

from echo_parse import TABLES


def retire_other_releases(release_id: str, *, client: Any, conn: Any) -> list[str]:
    """Keep only ``release_id`` data and archive prior published ECHO releases."""

    with conn.cursor() as cur:
        cur.execute("set statement_timeout = 0")
        for table in reversed(TABLES):
            cur.execute(f"delete from {table} where release_id <> %s", (release_id,))
    conn.commit()

    old = (
        client.table("common_dataset_release")
        .select("release_id")
        .eq("dataset", "echo")
        .eq("status", "published")
        .neq("release_id", release_id)
        .execute()
        .data
    )
    archived = [str(row["release_id"]) for row in old]
    for old_release_id in archived:
        client.table("common_dataset_release").update({"status": "archived"}).eq(
            "release_id", old_release_id
        ).execute()

    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for table in TABLES:
                cur.execute(f"vacuum analyze {table}")
    finally:
        conn.autocommit = False
    return archived
