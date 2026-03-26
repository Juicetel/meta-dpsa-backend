# Workflow: reindex.md
**Version:** 1.0
**Last Updated:** 2026-03-06
**Owner:** AI Team

---

## Objective
Execute a full re-index of the bot's knowledge base by querying Postgres/pgvector for the latest document chunks. This workflow is called by `document_ingest.md` after a valid S3 trigger is received. It keeps the bot's knowledge current and aligned with the latest scraped DPSA content.

---

## When This Runs
- **Triggered by:** `document_ingest.md` after validating an S3 Event Notification
- **Frequency:** On every completed scrape run (push-based, not scheduled)
- **Manual trigger:** Only by the AI Team for debugging — must be logged

---

## Required Inputs
| Input | Type | Required | Notes |
|-------|------|----------|-------|
| `scrape_timestamp` | str | Yes | ISO timestamp from the S3 trigger event |
| `trigger_type` | str | Yes | `"s3_event"` or `"manual"` |

---

## Steps

### Step 1 — Connect to Postgres/pgvector
**Tool:** `tools/reindexer.py`
- Uses `PGVECTOR_*` credentials from `.env`
- Verify connection before proceeding
- Output: active database connection

### Step 2 — Fetch New/Updated Chunks
**Tool:** `tools/reindexer.py`
- Query `document_chunks` table for all entries where `scraped_at >= last_reindex_timestamp`
- On first run (no prior timestamp): fetch all chunks
- Store `scrape_timestamp` as the new `last_reindex_timestamp` after successful fetch
- Output: `new_chunks` list

### Step 3 — Validate Fetched Chunks
**Agent action:**
- Check that each chunk has: non-empty `content`, valid `embedding` vector, `source_url`, `scraped_at`
- Log and skip any malformed chunks — do NOT crash the reindex for bad data
- Output: `valid_chunks`, `skipped_chunk_ids`

### Step 4 — Update Index
**Tool:** `tools/reindexer.py`
- Write `valid_chunks` into the local index cache (if applicable) OR confirm pgvector is the authoritative index and no local copy is needed
- Update `last_reindex_timestamp` to `scrape_timestamp`
- Output: `chunks_indexed`, `duration_ms`

### Step 5 — Return Result
- Return summary to `document_ingest.md` for logging
- Output:
```json
{
  "status": "success",
  "chunks_indexed": 142,
  "skipped_chunks": 2,
  "duration_ms": 1840,
  "last_reindex_timestamp": "2026-03-06T02:00:00Z"
}
```

---

## Edge Cases

| Situation | Action |
|-----------|--------|
| pgvector connection fails | Return error, do NOT update timestamp. Retry on next trigger. |
| Zero valid chunks returned | Log warning, keep previous index, raise with AWS team |
| Malformed chunk in batch | Skip that chunk, continue with rest, log skipped IDs |
| Reindex takes > 30s | Log slow reindex, investigate with AWS team |
| Duplicate trigger within 60s | Skip re-index, return "already current" status |

---

## Known Issues & Notes
*Append findings here as the system evolves.*

- [ ] Decide on incremental vs full re-index strategy with AWS team
- [ ] Implement `last_reindex_timestamp` persistence (file, env var, or DB record)
- [ ] Set up retry logic for connection failures
