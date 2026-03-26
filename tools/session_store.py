"""
Tool: session_store.py
Responsibility: Read and write conversation session context.
Tracks conversation history per session_id for multi-turn coherence.

WAT Role: Tools layer — deterministic execution only.
Called by: query_handler.md (Steps 5, 11)

Backend options (set SESSION_STORE_BACKEND in .env):
- "memory"  : In-process dict. Fast, no persistence across restarts.
- "redis"   : Persistent, shared across instances. Recommended for production.
- "postgres": Store sessions in Postgres alongside pgvector. Simplest for single-DB setups.
"""

import os
import json
from datetime import datetime, timezone

SESSION_STORE_BACKEND = os.getenv("SESSION_STORE_BACKEND", "memory")
REDIS_URL = os.getenv("REDIS_URL", "")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))  # 1 hour default
MAX_CONTEXT_TURNS = 10  # Keep last N turns per session

# In-memory store (fallback / development)
_memory_store: dict = {}


def load_session(session_id: str) -> dict:
    """
    Load conversation context for a session.

    Args:
        session_id: Unique session identifier.

    Returns:
        {
            "session_id": str,
            "history": [
                {"role": "user", "content": str, "language": str, "timestamp": str},
                {"role": "bot", "content": str, "language": str, "timestamp": str},
                ...
            ],
            "language": str,        # Last detected language for this session
            "turn_count": int
        }
        Returns an empty session dict if session_id is new.
    """
    if SESSION_STORE_BACKEND == "memory":
        return _memory_store.get(session_id, _empty_session(session_id))

    elif SESSION_STORE_BACKEND == "redis":
        # TODO: Implement Redis backend
        # import redis
        # r = redis.from_url(REDIS_URL)
        # data = r.get(f"session:{session_id}")
        # return json.loads(data) if data else _empty_session(session_id)
        raise NotImplementedError("session_store.py: Redis backend not yet implemented.")

    elif SESSION_STORE_BACKEND == "postgres":
        # TODO: Implement Postgres backend
        raise NotImplementedError("session_store.py: Postgres backend not yet implemented.")

    else:
        raise ValueError(f"Unknown SESSION_STORE_BACKEND: '{SESSION_STORE_BACKEND}'")


def save_session(session_id: str, query: str, response: str, language: str):
    """
    Append a new turn to the session history.

    Args:
        session_id: Unique session identifier.
        query:      User's message for this turn (English or original).
        response:   Bot's response for this turn (English).
        language:   User's detected/selected language for this turn.
    """
    session = load_session(session_id)
    timestamp = datetime.now(timezone.utc).isoformat()

    session["history"].append({"role": "user", "content": query, "language": language, "timestamp": timestamp})
    session["history"].append({"role": "bot", "content": response, "language": language, "timestamp": timestamp})
    session["language"] = language
    session["turn_count"] = len(session["history"]) // 2

    # Keep only the last MAX_CONTEXT_TURNS turns (both sides)
    if len(session["history"]) > MAX_CONTEXT_TURNS * 2:
        session["history"] = session["history"][-(MAX_CONTEXT_TURNS * 2):]

    if SESSION_STORE_BACKEND == "memory":
        _memory_store[session_id] = session

    elif SESSION_STORE_BACKEND == "redis":
        # TODO: Implement Redis save
        raise NotImplementedError("session_store.py: Redis backend not yet implemented.")

    elif SESSION_STORE_BACKEND == "postgres":
        # TODO: Implement Postgres save
        raise NotImplementedError("session_store.py: Postgres backend not yet implemented.")


def _empty_session(session_id: str) -> dict:
    """Return an empty session structure for a new session."""
    return {
        "session_id": session_id,
        "history": [],
        "language": "en",
        "turn_count": 0,
    }


if __name__ == "__main__":
    # Quick test with in-memory backend
    sid = "test_session_001"
    save_session(sid, "What is the leave policy?", "The leave policy states...", "en")
    session = load_session(sid)
    print(f"Session: {json.dumps(session, indent=2)}")
