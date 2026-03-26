"""
Tool: logger.py
Responsibility: POPIA-compliant audit logging for all bot interactions.
Records query metadata, language, document IDs used, confidence scores,
latency, and input type. Does NOT store raw user content beyond what is
required for audit purposes.

WAT Role: Tools layer — deterministic execution only.
Called by: query_handler.md (Step 12), voice_handler.md (Step 5),
           document_ingest.md (Step 4), escalation.md (Step 4)

POPIA Compliance:
- No unnecessary PII stored
- Audio files purged after delivery (see tts_synthesizer.py)
- Logs are structured for auditability, not user surveillance
- Log retention policy must be agreed with the organisation's POPIA officer
"""

import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = Path(os.getenv("TMP_DIR", ".tmp")) / "logs"


def log_interaction(
    session_id: str,
    query: str,
    language: str,
    input_type: str = "text",
    used_chunk_ids: list = None,
    response_confidence: float = None,
    latency_ms: int = None,
    stt_confidence: float = None,
):
    """
    Write a POPIA-compliant audit record for a user interaction.

    Args:
        session_id:          Unique session identifier.
        query:               User query text (stored for audit — no raw PII beyond this).
        language:            ISO 639-1 code of the user's language.
        input_type:          "text", "voice", or "sticker".
        used_chunk_ids:      List of document chunk IDs used to generate the response.
        response_confidence: Confidence score of the generated response (0.0-1.0).
        latency_ms:          Total end-to-end latency in milliseconds.
        stt_confidence:      STT confidence score (voice interactions only).
    """
    record = {
        "log_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "input_type": input_type,
        "language": language,
        "query_length": len(query) if query else 0,
        "used_chunk_ids": used_chunk_ids or [],
        "response_confidence": response_confidence,
        "latency_ms": latency_ms,
        "stt_confidence": stt_confidence,
    }

    # NOTE: query text is NOT stored in the log by default — only its length.
    # If query content logging is required for audit purposes, it must be
    # explicitly approved under the organisation's POPIA policy.

    _write_log("interaction", record)


def log_escalation(
    session_id: str,
    query: str,
    language: str,
    escalation_reason: str,
    retrieved_chunk_count: int = 0,
):
    """
    Log an escalation event (no results, low confidence, out-of-scope, grounding failure).
    Escalation logs are reviewed to identify knowledge gaps and improve the system.
    """
    record = {
        "log_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "event_type": "escalation",
        "escalation_reason": escalation_reason,
        "language": language,
        "retrieved_chunk_count": retrieved_chunk_count,
        "query_length": len(query) if query else 0,
    }
    _write_log("escalation", record)


def log_reindex(
    trigger: dict,
    chunks_indexed: int,
    duration_ms: int,
    errors: list = None,
):
    """
    Log the result of a knowledge base reindex operation.
    """
    record = {
        "log_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "reindex",
        "trigger_source": trigger.get("source", "unknown"),
        "scrape_timestamp": trigger.get("scrape_timestamp"),
        "chunks_indexed": chunks_indexed,
        "duration_ms": duration_ms,
        "errors": errors or [],
    }
    _write_log("reindex", record)


def log_error(tool_name: str, error_message: str, context: dict = None):
    """
    Log a tool-level error for debugging and self-improvement tracking.
    """
    record = {
        "log_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "error",
        "tool": tool_name,
        "error_message": error_message,
        "context": context or {},
    }
    _write_log("error", record)


def _write_log(log_type: str, record: dict):
    """
    Write a log record to the appropriate log file.
    Format: one JSON object per line (newline-delimited JSON / NDJSON).
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"{log_type}_{date_str}.ndjson"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    if LOG_LEVEL == "DEBUG":
        print(f"[logger] {log_type}: {json.dumps(record)}")


if __name__ == "__main__":
    # Quick test
    log_interaction(
        session_id="test_001",
        query="What is the leave policy?",
        language="en",
        input_type="text",
        used_chunk_ids=["chunk_abc", "chunk_def"],
        response_confidence=0.91,
        latency_ms=1240,
    )
    print(f"Log written to: {LOG_DIR.resolve()}")
