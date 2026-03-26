"""
Tool: reindexer.py
Responsibility: Re-pull the latest document chunks from Postgres/pgvector
when triggered by an S3 Event Notification. Updates the knowledge base
timestamp so subsequent retrievals use fresh data.

WAT Role: Tools layer — deterministic execution only.
Called by: document_ingest.md (Step 2), reindex.md (Steps 1-4)

Database: Owned and maintained by the AWS/Scraping Team.
Trigger: S3 Event Notification (push-based, not polling).
"""

import os
import json
from pathlib import Path
from datetime import datetime, timezone

PGVECTOR_HOST = os.getenv("PGVECTOR_HOST", "")
PGVECTOR_PORT = int(os.getenv("PGVECTOR_PORT", "5432"))
PGVECTOR_DB = os.getenv("PGVECTOR_DB", "")
PGVECTOR_USER = os.getenv("PGVECTOR_USER", "")
PGVECTOR_PASSWORD = os.getenv("PGVECTOR_PASSWORD", "")
PGVECTOR_TABLE = os.getenv("PGVECTOR_TABLE", "document_chunks")

# Persist the last reindex timestamp between runs
REINDEX_STATE_FILE = Path(os.getenv("TMP_DIR", ".tmp")) / "reindex_state.json"


def reindex(scrape_timestamp: str = None) -> dict:
    """
    Re-query Postgres/pgvector for chunks updated since the last reindex.

    Args:
        scrape_timestamp: ISO timestamp from the S3 trigger event.
                          Used to identify new/updated chunks.

    Returns:
        {
            "status": "success" | "error",
            "chunks_indexed": int,
            "skipped_chunks": int,
            "duration_ms": int,
            "errors": list,
            "last_reindex_timestamp": str
        }

    Raises:
        RuntimeError: If the database connection fails.

    NOTE: On first run (no prior state), fetches all chunks.
    On subsequent runs, only fetches chunks where scraped_at > last_reindex_timestamp.
    This is incremental by default — confirm with AWS team if full refresh is ever needed.
    See reindex.md Known Issues.
    """
    start_time = datetime.now(timezone.utc)
    errors = []

    # Load last reindex timestamp
    last_timestamp = _load_last_reindex_timestamp()

    try:
        conn = _get_connection()
        cursor = conn.cursor()

        if last_timestamp:
            cursor.execute(
                f"SELECT id, content, source_url, source_title, category, doc_type, scraped_at "
                f"FROM {PGVECTOR_TABLE} WHERE scraped_at > %s",
                (last_timestamp,)
            )
        else:
            # First run — fetch everything
            cursor.execute(
                f"SELECT id, content, source_url, source_title, category, doc_type, scraped_at "
                f"FROM {PGVECTOR_TABLE}"
            )

        rows = cursor.fetchall()
        conn.close()

    except Exception as e:
        raise RuntimeError(f"reindexer.py: Database query failed: {e}")

    # Validate each chunk
    chunks_indexed = 0
    skipped_chunks = 0
    skipped_ids = []

    for row in rows:
        chunk_id, content, source_url, source_title, category, doc_type, scraped_at = row

        if not content or not source_url:
            skipped_chunks += 1
            skipped_ids.append(str(chunk_id))
            continue

        # TODO: If a local cache/index is maintained, update it here.
        # If pgvector is the authoritative index (no local cache), this step is a no-op
        # and we only need to update the timestamp. Confirm with AWS team.
        chunks_indexed += 1

    if skipped_ids:
        errors.append(f"Skipped {skipped_chunks} malformed chunks: {skipped_ids[:10]}")

    # Save new timestamp
    new_timestamp = scrape_timestamp or datetime.now(timezone.utc).isoformat()
    _save_last_reindex_timestamp(new_timestamp)

    duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

    return {
        "status": "success" if not errors else "partial",
        "chunks_indexed": chunks_indexed,
        "skipped_chunks": skipped_chunks,
        "duration_ms": duration_ms,
        "errors": errors,
        "last_reindex_timestamp": new_timestamp,
    }


def _load_last_reindex_timestamp() -> str | None:
    """Load the last reindex timestamp from the state file."""
    try:
        if REINDEX_STATE_FILE.exists():
            with open(REINDEX_STATE_FILE) as f:
                state = json.load(f)
                return state.get("last_reindex_timestamp")
    except Exception:
        pass
    return None


def _save_last_reindex_timestamp(timestamp: str):
    """Persist the last reindex timestamp to the state file."""
    REINDEX_STATE_FILE.parent.mkdir(exist_ok=True)
    with open(REINDEX_STATE_FILE, "w") as f:
        json.dump({"last_reindex_timestamp": timestamp}, f)


def _get_connection():
    """Create and return a Postgres connection."""
    try:
        import psycopg2
        return psycopg2.connect(
            host=PGVECTOR_HOST,
            port=PGVECTOR_PORT,
            dbname=PGVECTOR_DB,
            user=PGVECTOR_USER,
            password=PGVECTOR_PASSWORD,
        )
    except Exception as e:
        raise RuntimeError(f"reindexer.py: Failed to connect to Postgres: {e}")


if __name__ == "__main__":
    print("reindexer.py — running manual reindex...")
    try:
        result = reindex(trigger_type="manual")
        print(f"Result: {result}")
    except NotImplementedError as e:
        print(f"Not yet configured: {e}")
    except RuntimeError as e:
        print(f"Runtime error: {e}")
