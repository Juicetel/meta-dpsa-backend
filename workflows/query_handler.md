# Workflow: query_handler.md
**Version:** 1.0
**Last Updated:** 2026-03-06
**Owner:** AI Team

---

## Objective
Handle an incoming text, emoji, or sticker query from a DPSA user. Detect language, retrieve relevant content from the pgvector knowledge base, generate a grounded response using Llama 3.2-Vision, and return the response in the user's language alongside source links and follow-up suggestions.

---

## Required Inputs
| Input | Type | Required | Notes |
|-------|------|----------|-------|
| `query` | str | Yes | Raw user message (text, emoji, or combined) |
| `session_id` | str | Yes | Unique session identifier for context tracking |
| `language` | str | No | ISO 639-1 code if user has selected language explicitly |
| `image` | bytes / file | No | Sticker or image file (for Llama vision processing) |

---

## Steps

### Step 1 — Parse Emoji (if applicable)
**Tool:** `tools/emoji_parser.py`
- Call `parse_emojis(query)` to detect emoji Unicode characters
- Append semantic meaning to the query string
- If no emojis detected, pass query through unchanged
- Output: `enriched_query`

### Step 2 — Process Sticker/Image (if applicable)
**Agent action (no separate tool):** Llama 3.2-Vision
- If `image` is present, pass it to Llama's vision layer
- Extract the emotional intent or semantic content of the sticker
- Combine extracted meaning with `enriched_query`
- Output: `enriched_query` (updated with sticker context)

### Step 3 — Detect Language
**Tool:** `tools/lang_detector.py`
- Call `detect_language(enriched_query)`
- Returns `{"language": ISO_code, "confidence": float, "language_name": str}`
- If user has explicitly selected a language, override the detected language
- Output: `source_language`, `lang_confidence`

### Step 4 — Translate to English (if not English)
**Tool:** `tools/translator.py`
- If `source_language != "en"`: call `translate(enriched_query, source_lang=source_language, target_lang="en")`
- If already English, skip this step
- Output: `english_query`

### Step 5 — Load Session Context
**Tool:** `tools/session_store.py`
- Call `load_session(session_id)` to retrieve conversation history
- Returns last N turns of context for grounding
- Output: `session_context`

### Step 6 — Retrieve Relevant Chunks
**Tool:** `tools/retriever.py`
- Call `retrieve(english_query, top_k=MAX_RETRIEVAL_CHUNKS)`
- Performs vector similarity search against Postgres/pgvector (AWS team's database)
- Returns ranked chunks with metadata: content, source_url, source_title, category, doc_type, scraped_at
- Output: `retrieved_chunks`

**Edge case:** If `retrieved_chunks` is empty → proceed to escalation.md workflow.

### Step 7 — Generate Response
**Agent action:** Llama 3.2-Vision
- Read `prompts/system_prompt.md` for grounding constraints
- Pass `english_query`, `session_context`, and `retrieved_chunks` to Llama
- Instruction: Generate a response using ONLY the information in the retrieved chunks. Do not invent, extrapolate, or use training knowledge about DPSA. Cite sources.
- Output: `english_response`, `used_chunk_ids`, `response_confidence`

### Step 8 — Grounding Check
**Agent action:** Validate before continuing
- Verify that every claim in `english_response` is supported by text in `retrieved_chunks`
- If `response_confidence < RESPONSE_CONFIDENCE_THRESHOLD`: route to escalation.md
- If grounding fails: discard response and escalate, do NOT return ungrounded content
- Output: `grounded_response`

### Step 9 — Translate Response to User Language
**Tool:** `tools/translator.py`
- If `source_language != "en"`: call `translate(grounded_response, source_lang="en", target_lang=source_language)`
- If already English, skip this step
- Output: `final_response`

### Step 10 — Generate Follow-Up Suggestions
**Tool:** `tools/followup_generator.py`
- Call `generate_followups(english_query, grounded_response, retrieved_chunks)`
- Returns 2-3 contextually relevant follow-up questions in the user's language
- Output: `followups`

### Step 11 — Save Session Context
**Tool:** `tools/session_store.py`
- Call `save_session(session_id, query=enriched_query, response=grounded_response, language=source_language)`
- Output: session updated

### Step 12 — Log Interaction
**Tool:** `tools/logger.py`
- Call `log_interaction(session_id, query, source_language, used_chunk_ids, response_confidence, input_type="text")`
- POPIA-compliant: no PII stored beyond what is required for audit
- Output: audit record written

---

## Expected Outputs
```json
{
  "response": "Final response in user's language",
  "source_links": [
    {"title": "Source title", "url": "https://..."}
  ],
  "followups": [
    "Follow-up question 1",
    "Follow-up question 2"
  ],
  "language": "zu",
  "confidence": 0.87
}
```

---

## Edge Cases

| Situation | Action |
|-----------|--------|
| No chunks retrieved | Route to `escalation.md` |
| `response_confidence < threshold` | Route to `escalation.md` |
| Language detection confidence < 0.5 | Default to English, note uncertainty in response |
| Unsupported language detected | Respond in English, notify user |
| Sticker intent unclear | Treat as text-only query |
| Translator API failure | Return English response with note that translation is unavailable |
| pgvector connection failure | Return service unavailable message, log error |

---

## Known Issues & Notes

### Phase 1 scope (text-to-text, multilingual)
- This workflow covers Phase 1 fully. Voice input path (Step 0: STT) is Phase 2.
- [ ] Confirm pgvector schema matches `retriever.py` expectations with AWS team before go-live
