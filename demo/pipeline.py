"""
Pipeline: pipeline.py
Implements the full 12-step query_handler.md workflow.
Called by api/main.py (FastAPI) which serves the Nuxt frontend.

Pending production swap:
  - tools/groq_client.py -> tools/llama_client.py (when AWS EC2 Llama endpoint is ready)
"""

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    str(PROJECT_ROOT / "google-credentials.json"),
)

# ── TOOL IMPORTS ──────────────────────────────────────────────────────────────
from tools.emoji_parser import parse_emojis
from tools.lang_detector import detect_language
from tools.translator import translate_text
from tools.session_store import load_session, save_session
from tools.retriever import retrieve
from tools.groq_client import generate_response     # SWAP -> tools.llama_client when EC2 ready
from tools.followup_generator import generate_followups
from tools.logger import log_interaction, log_escalation, log_error

LOW_CONFIDENCE_THRESHOLD = 0.5

_LOW_CONFIDENCE_CAVEAT = (
    "\n\n*Note: I am not fully confident this fully answers your question. "
    "For a definitive answer, please visit www.dpsa.gov.za "
    "or contact DPSA at info@dpsa.gov.za.*"
)


def run_pipeline(query: str, session_id: str, images: list | None = None) -> dict:
    """
    Execute the full 12-step query_handler.md pipeline.

    Args:
        query:      Raw user input (any supported language, may contain emoji).
        session_id: Unique session identifier for context tracking.

    Returns:
        {
            "response":      str,   # Final response in user's language
            "source_links":  list,  # [{"title": str, "url": str}, ...]
            "followups":     list,  # Follow-up question strings in user's language
            "language":      str,   # ISO 639-1 code of user's language
            "confidence":    float, # Response confidence 0.0-1.0
            "steps":         list,  # Step log entries for UI display
        }
    """
    start_time = time.time()
    steps = []

    def log_step(n: int, name: str, detail: str = ""):
        steps.append({"step": n, "name": name, "detail": detail})

    # ── STEP 1: Parse emojis ──────────────────────────────────────────────────
    try:
        emoji_result = parse_emojis(query)
        enriched_query = emoji_result["enriched_query"]
        if emoji_result.get("has_emojis"):
            log_step(1, "Parse emojis", f"found: {', '.join(emoji_result.get('emoji_meanings', []))}")
        else:
            log_step(1, "Parse emojis", "no emojis detected")
    except Exception as e:
        enriched_query = query
        log_step(1, "Parse emojis", f"error: {e}")

    # ── STEP 2: Process sticker/image -- SKIP (Phase 2) ──────────────────────
    log_step(2, "Process image/sticker", "skipped (Phase 2 -- text only)")

    # ── STEP 3: Detect language ───────────────────────────────────────────────
    source_language = "en"
    lang_confidence = 1.0
    lang_name = "English"
    lang_is_supported = True
    lang_result = {}

    try:
        lang_result = detect_language(enriched_query)
        source_language = lang_result["language"]
        lang_confidence = lang_result["confidence"]
        lang_name = lang_result["language_name"]
        lang_is_supported = lang_result.get("is_supported", False)
        log_step(3, "Detect language", f"{lang_name} ({source_language}) -- conf: {lang_confidence:.2f}")
    except Exception as e:
        log_step(3, "Detect language", f"error: {e} -- defaulting to English")
        log_error("lang_detector", str(e), {"session_id": session_id})

    # ── STEP 4: Translate to English ──────────────────────────────────────────
    english_query = enriched_query
    if source_language != "en" and lang_is_supported:
        try:
            tr = translate_text(enriched_query, source_language, "en")
            english_query = tr["translated_text"]
            preview = english_query[:60] + "..." if len(english_query) > 60 else english_query
            log_step(4, "Translate to English", f'"{preview}"')
        except Exception as e:
            log_step(4, "Translate to English", f"error: {e} -- using original query")
            log_error("translator", str(e), {"session_id": session_id})
    else:
        log_step(4, "Translate to English", "skipped (already English)")

    # ── STEP 5: Load session context ─────────────────────────────────────────
    session_context = {"session_id": session_id, "history": [], "language": "en", "turn_count": 0}
    try:
        session_context = load_session(session_id)
        turn = session_context.get("turn_count", 0)
        log_step(5, "Load session context", f"turn {turn + 1} in this session")
    except Exception as e:
        log_step(5, "Load session context", f"error: {e} -- proceeding without context")

    # ── STEP 6: Retrieve relevant chunks ─────────────────────────────────────
    retrieved_chunks = []
    try:
        retrieved_chunks = retrieve(english_query, top_k=5)
        if retrieved_chunks:
            top_score = retrieved_chunks[0]["similarity_score"]
            log_step(6, "Retrieve chunks", f"{len(retrieved_chunks)} chunks found -- top score: {top_score:.3f}")
        else:
            log_step(6, "Retrieve chunks", "no results -- escalating")
            return _escalation(
                session_id, enriched_query, source_language, 0, "no_results", steps
            )
    except Exception as e:
        log_step(6, "Retrieve chunks", f"error: {e}")
        log_error("retriever", str(e), {"session_id": session_id})
        return _escalation(session_id, enriched_query, source_language, 0, "no_results", steps)

    # ── STEP 7: Generate response ─────────────────────────────────────────────
    english_response = ""
    used_chunk_ids = []
    response_confidence = 0.0

    try:
        llm_result = generate_response(english_query, session_context, retrieved_chunks, images=images)
        english_response = llm_result["english_response"]
        used_chunk_ids = llm_result["used_chunk_ids"]
        response_confidence = llm_result["response_confidence"]
        log_step(7, "Generate response", f"confidence: {response_confidence:.2f}")
    except Exception as e:
        log_step(7, "Generate response", f"error: {e}")
        log_error("llm_client", str(e), {"session_id": session_id})
        return _escalation(
            session_id, enriched_query, source_language,
            len(retrieved_chunks), "grounding_failure", steps
        )

    # ── STEP 8: Grounding check ───────────────────────────────────────────────
    if response_confidence < LOW_CONFIDENCE_THRESHOLD:
        log_step(
            8, "Grounding check",
            f"low confidence ({response_confidence:.2f}) -- adding caveat"
        )
        grounded_response = english_response + _LOW_CONFIDENCE_CAVEAT
    else:
        log_step(8, "Grounding check", "passed")
        grounded_response = english_response

    # ── STEP 9: Translate response back to user language ─────────────────────
    final_response = grounded_response
    if source_language != "en" and lang_is_supported:
        try:
            back = translate_text(grounded_response, "en", source_language)
            final_response = back["translated_text"]
            log_step(9, "Translate response", f"translated to {lang_name}")
        except Exception as e:
            log_step(9, "Translate response", f"error: {e} -- returning English")
    else:
        log_step(9, "Translate response", "skipped (already English)")

    # ── STEP 10: Generate follow-up suggestions ───────────────────────────────
    followups = []
    try:
        followups_en = generate_followups(english_query, grounded_response, retrieved_chunks)
        if source_language != "en" and lang_is_supported:
            followups = []
            for q in followups_en:
                try:
                    t = translate_text(q, "en", source_language)
                    followups.append(t["translated_text"])
                except Exception:
                    followups.append(q)
        else:
            followups = followups_en
        log_step(10, "Generate follow-ups", f"{len(followups)} suggestions")
    except Exception as e:
        log_step(10, "Generate follow-ups", f"error: {e} -- skipping")

    # ── STEP 11: Save session context ─────────────────────────────────────────
    try:
        save_session(session_id, enriched_query, grounded_response, source_language)
        log_step(11, "Save session", "saved")
    except Exception as e:
        log_step(11, "Save session", f"error: {e}")

    # ── STEP 12: Log interaction ──────────────────────────────────────────────
    latency_ms = int((time.time() - start_time) * 1000)
    try:
        log_interaction(
            session_id=session_id,
            query=enriched_query,
            language=source_language,
            input_type="text",
            used_chunk_ids=used_chunk_ids,
            response_confidence=response_confidence,
            latency_ms=latency_ms,
        )
        log_step(12, "Log interaction", f"logged -- latency: {latency_ms}ms")
    except Exception as e:
        log_step(12, "Log interaction", f"error: {e}")

    # ── BUILD SOURCE LINKS ────────────────────────────────────────────────────
    source_links = []
    seen_urls = set()
    for chunk in retrieved_chunks:
        if chunk.get("id", "") in used_chunk_ids:
            url = chunk.get("source_url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                source_links.append({
                    "title": chunk.get("source_title", ""),
                    "url": url,
                })

    return {
        "response": final_response,
        "source_links": source_links,
        "followups": followups,
        "language": source_language,
        "confidence": response_confidence,
        "steps": steps,
    }


def _escalation(
    session_id: str,
    query: str,
    language: str,
    chunk_count: int,
    reason: str,
    steps: list,
) -> dict:
    """Return a graceful escalation response and log the event."""
    try:
        log_escalation(session_id, query, language, reason, chunk_count)
    except Exception:
        pass

    messages = {
        "no_results": (
            "I was not able to find specific information about that in the DPSA "
            "knowledge base. For accurate information please visit www.dpsa.gov.za "
            "or contact DPSA at info@dpsa.gov.za."
        ),
        "low_confidence": (
            "I found some related information but I am not confident it fully "
            "answers your question. For a definitive answer please visit "
            "www.dpsa.gov.za or contact DPSA directly at +27 12 336 1000."
        ),
        "grounding_failure": (
            "I was not able to provide a reliable answer with the information "
            "currently available. Please visit www.dpsa.gov.za for the most "
            "accurate and up-to-date information."
        ),
    }
    msg = messages.get(reason, messages["no_results"])

    if language != "en":
        try:
            t = translate_text(msg, "en", language)
            msg = t["translated_text"]
        except Exception:
            pass

    steps.append({"step": 99, "name": "Escalation", "detail": f"reason: {reason}"})

    return {
        "response": msg,
        "source_links": [],
        "followups": [],
        "language": language,
        "confidence": 0.0,
        "steps": steps,
    }
