# Workflow: voice_handler.md
**Version:** 1.2
**Last Updated:** 2026-03-09
**Owner:** AI Team

> **PHASE 2 — NOT IN CURRENT SCOPE**
> The bot is text-to-text for Phase 1. Voice input (STT) and voice output (TTS) are
> deferred to Phase 2. This workflow is preserved for planning purposes only.
> Do not implement `stt_transcriber.py` or `tts_synthesizer.py` until Phase 2 begins.

---

## Objective
Handle a voice input from a DPSA user. Transcribe audio, detect language, route through the standard query pipeline, and return both a text response and an audio file synthesized in the user's language.

---

## Required Inputs
| Input | Type | Required | Notes |
|-------|------|----------|-------|
| `audio_file` | bytes / file path | Yes | Multipart audio from UI/UX widget |
| `session_id` | str | Yes | Unique session identifier |
| `selected_language` | str | No | ISO 639-1 code if user has selected language in UI |

---

## Steps

### Step 1 — Transcribe Audio (STT)
**Tool:** `tools/stt_transcriber.py`
- Call `transcribe(audio_file, language_hint=selected_language)`
- Returns `{"transcript": str, "confidence": float, "detected_language": str}`
- Use `selected_language` as a hint if provided — improves accuracy for SA languages
- Output: `transcript`, `stt_confidence`, `detected_language`

**Edge case:** If `stt_confidence < STT_CONFIDENCE_THRESHOLD` → prompt user to repeat or switch to text. Do NOT proceed with low-confidence transcript.

### Step 2 — Confirm Language
**Tool:** `tools/lang_detector.py`
- Call `detect_language(transcript)` to confirm or correct the STT language detection
- If `selected_language` was provided and confidence is high, trust the selection
- Output: `confirmed_language`

### Step 3 — Hand off to Text Query Pipeline
- Pass `transcript` and `confirmed_language` to `query_handler.md` workflow
- Voice queries follow the exact same retrieval → generation → grounding → translation path
- Do NOT skip any steps from `query_handler.md`
- Output: `english_response`, `final_response` (in confirmed_language), `source_links`, `followups`

### Step 4 — Synthesize Audio Response (TTS)
**Tool:** `tools/tts_synthesizer.py`
- Call `synthesize(final_response, language=confirmed_language)`
- Returns path to audio file stored in `.tmp/`
- Generate a time-limited signed URL or relative path for the UI to play
- Audio files are purged from `.tmp/` after `AUDIO_TTL_SECONDS` (POPIA compliance — no voice recordings stored permanently)
- Output: `audio_url`

**Edge case:** If TTS fails for the confirmed language → return text response only. Log the gap in Known Issues below.

### Step 5 — Log Interaction
**Tool:** `tools/logger.py`
- Call `log_interaction(session_id, query=transcript, language=confirmed_language, input_type="voice", stt_confidence=stt_confidence)`
- Log includes: STT confidence, language detected, doc IDs used, response confidence, latency
- No audio content or raw transcript stored beyond what is required for audit
- Output: audit record written

---

## Expected Outputs
```json
{
  "response": "Final response in user's language",
  "audio_url": ".tmp/audio_<session_id>_<timestamp>.mp3",
  "source_links": [
    {"title": "Source title", "url": "https://..."}
  ],
  "followups": [
    "Follow-up question 1",
    "Follow-up question 2"
  ],
  "language": "af",
  "stt_confidence": 0.92
}
```

---

## Edge Cases

| Situation | Action |
|-----------|--------|
| `stt_confidence < threshold` | Prompt user to repeat or switch to text. Do not process. |
| Language not supported by STT | Return error message in English, suggest text input |
| Language not supported by TTS | Return text response only, log gap in Known Issues |
| Audio file format not supported | Return format error, list supported formats |
| Transcript is too short / empty | Ask user to speak their question more clearly |
| TTS synthesis takes > 3s | Return text immediately, stream audio when ready |

---

## Supported Audio Formats
*Validate with `stt_transcriber.py` provider before go-live.*
- WAV, MP3, OGG, FLAC, M4A (subject to STT provider support)

---

## STT & TTS Coverage — Validated 2026-03-09

Research across Google Cloud, Azure, and AWS. Results are sobering — no mainstream provider
covers all 11 SA languages for voice.

### STT (Speech-to-Text)
**Selected provider: Google Cloud STT V2** — best SA language coverage of any mainstream provider.

| Language | ISO Code | Google STT | Azure STT | AWS Transcribe |
|----------|----------|-----------|-----------|----------------|
| English | en-ZA | ✅ | ✅ | ✅ |
| Afrikaans | af-ZA | ✅ | ✅ | ✅ |
| isiZulu | zu-ZA | ✅ | ✅ | ✅ |
| isiXhosa | xh-ZA | ✅ | ❌ | ❌ |
| Sepedi | nso-ZA | ✅ | ❌ | ❌ |
| Setswana | tn-ZA | ❌ | ❌ | ❌ |
| Sesotho | st-ZA | ❌ | ❌ | ❌ |
| Xitsonga | ts-ZA | ❌ | ❌ | ❌ |
| siSwati | ss-ZA | ❌ | ❌ | ❌ |
| Tshivenda | ve-ZA | ❌ | ❌ | ❌ |
| isiNdebele | nr-ZA | ❌ | ❌ | ❌ |

**Google STT covers 5/11. No provider covers more.**
For the 6 unsupported STT languages: voice input is not available. User must use text input.

### TTS (Text-to-Speech)
**Critical gap: no mainstream provider covers more than 3/11 SA languages for TTS.**

| Language | ISO Code | Google TTS | Azure TTS | AWS Polly |
|----------|----------|-----------|-----------|-----------|
| English | en-ZA | ✅ (en-ZA) | ✅ | ✅ (Ayanda) |
| Afrikaans | af-ZA | ✅ (af-ZA-Standard-A) | ✅ | ❌ |
| isiZulu | zu-ZA | ❌ | ✅ | ❌ |
| isiXhosa | xh-ZA | ❌ | ❌ | ❌ |
| Sepedi | nso-ZA | ❌ | ❌ | ❌ |
| Setswana | tn-ZA | ❌ | ❌ | ❌ |
| Sesotho | st-ZA | ❌ | ❌ | ❌ |
| Xitsonga | ts-ZA | ❌ | ❌ | ❌ |
| siSwati | ss-ZA | ❌ | ❌ | ❌ |
| Tshivenda | ve-ZA | ❌ | ❌ | ❌ |
| isiNdebele | nr-ZA | ❌ | ❌ | ❌ |

**Decision: Use Azure TTS as primary** (covers en-ZA, af-ZA, zu-ZA).
Use **Google TTS** as fallback for af-ZA (has a dedicated af-ZA-Standard-A voice).
For all other languages: **text-only response**. No audio. Notify user.

### Recommended Provider Stack (Voice)
| Capability | Provider | Covered Languages |
|-----------|---------|------------------|
| STT | Google Cloud STT V2 | en, af, zu, xh, nso (5/11) |
| TTS | Azure Cognitive Services | en-ZA, af-ZA, zu-ZA (3/11) |
| TTS fallback | Google Cloud TTS | af-ZA only |

### Known Issues & Action Items
- [ ] Confirm max audio file size limit with UI/UX team
- [ ] Confirm audio file purge mechanism (cron job or post-delivery hook)
- [ ] **Escalate TTS gap to project stakeholders** — voice output in Setswana, Sesotho,
  Xitsonga, siSwati, Tshivenda, isiNdebele, isiXhosa is not achievable with mainstream providers.
  Alternatives to evaluate:
  - **Lelapa AI** (SA startup, indigenous language focus) — contact for API access
  - **CSIR / SADiLaR** — research-grade models, may have TTS for more SA languages
  - **Microsoft Azure Custom Neural Voice** — could train a custom voice but requires data + cost
- [x] STT provider validated: Google Cloud STT V2
- [x] TTS provider validated: Azure Cognitive Services (primary)
