# Workflow: document_ingest.md
**Version:** 1.0
**Last Updated:** 2026-03-06
**Owner:** AI Team

---

## Objective
On receipt of an S3 Event Notification trigger from the AWS/Scraping Team, pull the latest document chunks and embeddings from the Postgres/pgvector database and re-index the bot's knowledge base. This workflow keeps the bot's knowledge current without polling.

---

## Trigger
This workflow is initiated by an **S3 Event Notification** fired by the AWS/Scraping Team when a scrape run completes. It is NOT triggered manually or on a schedule. The trigger is push-based and must result in an immediate re-index.

See `workflows/aws_data_sync.md` for the full integration protocol with the AWS team.

---

## Required Inputs
| Input | Type | Required | Notes |
|-------|------|----------|-------|
| `s3_event` | dict | Yes | S3 Event Notification payload from AWS |
| `trigger_source` | str | Yes | `"s3_event"` — used to validate trigger origin |

---

## Steps

### Step 1 — Validate Trigger
**Agent action:**
- Confirm `trigger_source == "s3_event"`
- Parse `s3_event` payload: extract bucket name, key prefix, timestamp
- Verify bucket name matches `S3_BUCKET_NAME` from `.env`
- If validation fails: log error and halt. Do NOT proceed with re-index.
- Output: `validated_event`, `scrape_timestamp`

### Step 2 — Execute Re-Index
**Tool:** `tools/reindexer.py`
- Call `reindex(scrape_timestamp=scrape_timestamp)`
- Tool connects to Postgres/pgvector (credentials from `.env`)
- Queries for all chunks with `scraped_at > last_reindex_timestamp`
- Updates the local query cache / index pointer
- Returns `{"chunks_indexed": int, "errors": list, "duration_ms": int}`
- Output: `reindex_result`

### Step 3 — Validate Re-Index Result
**Agent action:**
- If `reindex_result["errors"]` is non-empty: log each error, raise alert, document in Known Issues below
- If `chunks_indexed == 0`: log warning — scrape may have produced no new data. Check with AWS team.
- If successful: log success with chunk count and duration

### Step 4 — Log Completion
**Tool:** `tools/logger.py`
- Call `log_reindex(trigger=s3_event, chunks_indexed=reindex_result["chunks_indexed"], duration_ms=reindex_result["duration_ms"], errors=reindex_result["errors"])`
- Output: audit record written

---

## Expected Outputs
```json
{
  "status": "success",
  "chunks_indexed": 142,
  "duration_ms": 1840,
  "scrape_timestamp": "2026-03-06T02:00:00Z",
  "errors": []
}
```

---

## Edge Cases

| Situation | Action |
|-----------|--------|
| pgvector connection failure | Log error, return failure response, do NOT crash bot |
| Zero chunks returned | Log warning, notify AWS team via documented channel |
| Malformed chunk data | Log malformed chunk IDs, skip malformed entries, continue with valid chunks |
| Duplicate trigger received | Check last reindex timestamp — skip if already processed within 60 seconds |
| Re-index takes > 30s | Log slow reindex, consider batching with AWS team |

---

## Known Issues & Notes
*Append findings here as the system evolves.*

- [ ] Confirm S3 Event Notification payload format with AWS team
- [ ] Confirm pgvector schema (see `aws_data_sync.md` Section 2) matches `reindexer.py` queries
- [ ] Decide: does `reindexer.py` do full refresh or incremental? Agree with AWS team before implementation.
