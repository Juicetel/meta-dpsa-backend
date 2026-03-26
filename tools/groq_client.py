"""
Tool: groq_client.py
Responsibility: Generate a grounded response using the Groq API (Llama 3.3 70B).
Production replacement for llm_client.py (Claude/Anthropic stand-in).

WAT Role: Tools layer -- deterministic execution only.
Called by: demo/pipeline.py (Step 7)

SWAP TO PRODUCTION:
  This file IS the production LLM client. When the AWS EC2 Llama endpoint becomes
  available, implement tools/llama_client.py with the same generate_response()
  signature and update the import in demo/pipeline.py. Keep this file as the
  Groq-hosted fallback.

Credentials: GROQ_API_KEY in .env
Model:       GROQ_MODEL in .env (default: llama-3.3-70b-versatile)
"""

import os
from pathlib import Path

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.md"

_client = None


def _get_client() -> Groq:
    """Return a cached Groq client."""
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise RuntimeError(
                "groq_client.py: GROQ_API_KEY not set in .env. "
                "Get a free key at https://console.groq.com and add it to .env."
            )
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def _load_system_prompt() -> str:
    """Read the system prompt from prompts/system_prompt.md."""
    try:
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RuntimeError(
            f"groq_client.py: System prompt not found at {SYSTEM_PROMPT_PATH}"
        )


def _format_chunks_as_context(retrieved_chunks: list) -> str:
    """
    Format retrieved chunks into a numbered context block for the user message.
    Structured so the model can accurately cite sources.
    """
    if not retrieved_chunks:
        return "No relevant documents were found in the knowledge base."

    lines = ["RETRIEVED DOCUMENTS:\n"]
    for i, chunk in enumerate(retrieved_chunks, start=1):
        lines.append(f"[CHUNK {i}]")
        lines.append(
            f"Source: {chunk.get('source_title', 'Unknown')} ({chunk.get('doc_type', 'unknown')})"
        )
        lines.append(f"URL: {chunk.get('source_url', 'N/A')}")
        lines.append(f"Category: {chunk.get('category', 'N/A')}")
        lines.append("---")
        lines.append(chunk.get("content", ""))
        lines.append("")

    return "\n".join(lines)


def _format_session_context(session_context: dict) -> str:
    """
    Format the last 3 turns of session history as a conversation prefix.
    Returns an empty string if no history exists.
    """
    history = session_context.get("history", [])
    if not history:
        return ""

    recent = history[-6:] if len(history) > 6 else history

    lines = [
        "CONVERSATION HISTORY (for context only -- do not repeat this in your response):"
    ]
    for turn in recent:
        role = "User" if turn["role"] == "user" else "Assistant"
        lines.append(f"{role}: {turn['content']}")
    lines.append("")
    return "\n".join(lines)


def _infer_used_chunks(response_text: str, retrieved_chunks: list) -> list:
    """
    Infer which chunks were used to generate the response.

    Two signals:
    1. Explicit citation: the chunk's source_title or source_url appears verbatim
       in the response text (works for mock/keyword data).
    2. Semantic confidence: the retriever already scored the chunk >= 0.7 via
       vector similarity, meaning it was relevant. Trust the retriever ranking
       for real semantic search results (AWS API).

    Returns a list of chunk IDs.
    """
    used_ids = []
    response_lower = response_text.lower()

    for chunk in retrieved_chunks:
        chunk_id = chunk.get("id", "")
        url = chunk.get("source_url", "").lower()
        title = chunk.get("source_title", "").lower()
        title_fragment = title[:40] if len(title) > 40 else title
        similarity = chunk.get("similarity_score", 0.0)

        explicit_citation = (url and url in response_lower) or (
            title_fragment and title_fragment in response_lower
        )
        high_similarity = similarity >= 0.7

        if explicit_citation or high_similarity:
            used_ids.append(chunk_id)

    return used_ids


def generate_response(
    english_query: str,
    session_context: dict,
    retrieved_chunks: list,
) -> dict:
    """
    Generate a grounded response using the Groq API (Llama 3.3 70B).

    Args:
        english_query:    User query already translated to English.
        session_context:  Dict from session_store.load_session() containing
                          {"history": [...], "language": str, "turn_count": int}.
        retrieved_chunks: List of chunk dicts from mock_retriever.retrieve()
                          (or retriever.retrieve() in production).

    Returns:
        {
            "english_response":    str,    # Full response text in English
            "used_chunk_ids":      list,   # IDs of chunks cited in the response
            "response_confidence": float   # Estimated confidence 0.0-1.0
        }

    Raises:
        ValueError: If english_query is empty.
        RuntimeError: If the API call fails or GROQ_API_KEY is not set.
    """
    if not english_query or not english_query.strip():
        raise ValueError("english_query cannot be empty.")

    client = _get_client()
    system_prompt = _load_system_prompt()
    context_block = _format_chunks_as_context(retrieved_chunks)
    session_block = _format_session_context(session_context)

    # Build the user message with clearly labelled sections
    parts = []
    if session_block:
        parts.append(session_block)
    parts.append(context_block)
    parts.append(f"USER QUESTION:\n{english_query}")

    user_message = "\n\n".join(parts)

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
    except Exception as e:
        raise RuntimeError(f"groq_client.py: Groq API call failed: {e}")

    english_response = completion.choices[0].message.content

    # Infer which chunks were cited
    used_chunk_ids = _infer_used_chunks(english_response, retrieved_chunks)

    # Confidence heuristic based on citation rate
    if not retrieved_chunks:
        confidence = 0.0
    elif used_chunk_ids:
        confidence = min(len(used_chunk_ids) / max(len(retrieved_chunks), 1) + 0.4, 1.0)
    else:
        confidence = 0.3  # Response generated but no explicit citations detected

    return {
        "english_response": english_response,
        "used_chunk_ids": used_chunk_ids,
        "response_confidence": round(confidence, 2),
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from tools.mock_retriever import retrieve

    query = "How many days of annual leave do I get as a public servant?"
    chunks = retrieve(query, top_k=3)
    result = generate_response(query, {"history": []}, chunks)
    print("groq_client.py -- smoke test\n")
    print(f"Model: {GROQ_MODEL}")
    print(f"Query: {query}")
    print(f"Response confidence: {result['response_confidence']}")
    print(f"Used chunk IDs: {result['used_chunk_ids']}")
    print(f"\nResponse:\n{result['english_response']}".encode("utf-8", errors="replace").decode("utf-8"))
