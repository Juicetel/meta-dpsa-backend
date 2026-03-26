# Workflow: escalation.md
**Version:** 1.0
**Last Updated:** 2026-03-06
**Owner:** AI Team

---

## Objective
Handle situations where the bot cannot generate a confident, grounded response. Escalation includes low-confidence retrieval, empty results, unanswerable queries, and requests for information outside the DPSA public knowledge base. The goal is to give the user a clear, helpful response even when the bot cannot answer directly.

---

## Escalation Triggers

| Trigger | Condition |
|---------|-----------|
| No chunks retrieved | `retriever.py` returns 0 results |
| Low response confidence | `response_confidence < RESPONSE_CONFIDENCE_THRESHOLD` |
| Out-of-scope query | Query is clearly unrelated to DPSA public services |
| Grounding failure | Response cannot be verified against retrieved chunks |
| Repeated clarification failure | User has been asked to clarify twice without resolution |

---

## Required Inputs
| Input | Type | Required | Notes |
|-------|------|----------|-------|
| `query` | str | Yes | Original user query |
| `session_id` | str | Yes | Session identifier |
| `escalation_reason` | str | Yes | One of: `no_results`, `low_confidence`, `out_of_scope`, `grounding_failure` |
| `language` | str | Yes | ISO 639-1 code for response language |
| `retrieved_chunks` | list | No | Partial results if any were retrieved |

---

## Steps

### Step 1 — Classify Escalation Type
**Agent decision:**
- `no_results`: Nothing relevant found in the knowledge base
- `low_confidence`: Results found but response confidence is below threshold
- `out_of_scope`: Query is not about DPSA public services
- `grounding_failure`: Response generated but cannot be grounded to retrieved content

### Step 2 — Generate Escalation Response
**Agent action:** Read `prompts/system_prompt.md` for tone constraints
- Compose an honest, helpful response appropriate to the escalation type (see templates below)
- Never claim to have information you don't have
- Never fabricate contact details, policy references, or page URLs
- Always offer a next step the user can take

**Response templates:**

**no_results:**
> "I wasn't able to find specific information about that in the DPSA knowledge base. You may find what you're looking for on the official DPSA website at www.dpsa.gov.za, or by contacting the DPSA directly."

**low_confidence:**
> "I found some related information, but I'm not confident it fully answers your question. Here's what I found: [partial content]. For a definitive answer, please visit www.dpsa.gov.za or contact DPSA directly."

**out_of_scope:**
> "That question falls outside what I'm able to help with — I'm specifically set up to answer questions about DPSA public services and information. Is there something DPSA-related I can assist you with?"

**grounding_failure:**
> "I wasn't able to give you a reliable answer to that question with the information currently available. Please visit www.dpsa.gov.za for the most accurate and up-to-date information."

### Step 3 — Translate Escalation Response
**Tool:** `tools/translator.py`
- If `language != "en"`: translate the escalation response into the user's language
- Output: `final_escalation_response`

### Step 4 — Log Escalation
**Tool:** `tools/logger.py`
- Call `log_escalation(session_id, query, language, escalation_reason, retrieved_chunk_count)`
- Escalation logs are used to identify knowledge gaps and improve the system
- Output: audit record written

---

## Expected Outputs
```json
{
  "response": "Escalation response in user's language",
  "escalation_reason": "no_results",
  "source_links": [],
  "followups": []
}
```

---

## Edge Cases

| Situation | Action |
|-----------|--------|
| Escalation happens during voice flow | Return text + synthesize audio of escalation response |
| User asks the same question repeatedly | Log pattern, note in Known Issues — may indicate a knowledge gap |
| Translation of escalation response fails | Return English escalation response |

---

## Improvement Protocol
Escalation logs should be reviewed regularly to identify:
1. **Knowledge gaps**: Topics users ask about that aren't covered by the DPSA scrape
2. **Scraping gaps**: Pages or documents that should be in the knowledge base but aren't
3. **Confidence calibration**: If escalation rate is too high, review retrieval parameters

Document findings in Known Issues below and raise with the AWS team if it is a scraping gap.

---

## Known Issues & Notes
*Append findings here as the system evolves.*

- [ ] Review escalation logs after first week of deployment to identify knowledge gaps
- [ ] Confirm official DPSA contact details to include in escalation responses (do NOT hardcode — use retrieved chunks if possible)
