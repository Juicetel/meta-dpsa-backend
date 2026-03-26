# Workflow: language_router.md
**Version:** 1.2
**Last Updated:** 2026-03-09
**Owner:** AI Team

---

## Objective
Detect the language of an incoming text query and route it through the correct translation path. All retrieval and generation happens in English internally. This workflow ensures every query enters the pipeline as English and every response exits in the user's language.

**Phase 1 scope:** Text-to-text only. STT and TTS are Phase 2 — see `voice_handler.md`.

---

## Supported Languages — Validated 2026-03-09

Translation is handled by **Google Cloud Translate** (best SA coverage of mainstream providers).
STT/TTS coverage is deferred to Phase 2 and documented in `voice_handler.md`.

| Language | ISO Code | Google Translate | Notes |
|----------|----------|-----------------|-------|
| English | en | ✅ Supported | Baseline |
| Afrikaans | af | ✅ Supported | |
| isiZulu | zu | ✅ Supported | |
| isiXhosa | xh | ✅ Supported | |
| Sepedi (Northern Sotho) | nso | ✅ Supported | Google uses `nso` (not `sep`) |
| Setswana | tn | ✅ Supported | |
| Sesotho | st | ✅ Supported | |
| Xitsonga | ts | ✅ Supported | |
| siSwati | ss | ✅ Supported | |
| Tshivenda | ve | ❌ NOT supported | Fallback: English |
| isiNdebele | nr | ❌ NOT supported | Fallback: English |

**Decision:** Use Google Cloud Translate. 9/11 SA languages supported.
For `ve` and `nr`: respond in English, inform user their language is not yet available.

---

## Required Inputs
| Input | Type | Required | Notes |
|-------|------|----------|-------|
| `text` | str | Yes | Incoming query text or transcript |
| `explicit_language` | str | No | ISO code if user selected language in UI |

---

## Steps

### Step 1 — Language Detection
**Tool:** `tools/lang_detector.py`
- Call `detect_language(text)`
- Returns `{"language": ISO_code, "confidence": float}`
- If `explicit_language` is provided AND confidence >= 0.5: override detection with `explicit_language`
- Output: `detected_language`, `detection_confidence`

### Step 2 — Confidence Check
**Agent decision:**
- If `detection_confidence >= 0.8`: use `detected_language` with high confidence
- If `0.5 <= detection_confidence < 0.8`: use `detected_language` but flag as uncertain
- If `detection_confidence < 0.5`: default to English, note uncertainty in response to user

### Step 3 — Validate Language Support
**Agent decision:**
- Check if `detected_language` is in the supported languages list above
- If NOT supported: respond in English, inform user that their language is not yet supported, invite them to use English or Afrikaans as alternatives

### Step 4 — Translate Query to English (if needed)
**Tool:** `tools/translator.py`
- If `detected_language != "en"`: call `translate(text, source_lang=detected_language, target_lang="en")`
- If already English: skip
- Output: `english_text`

### Step 5 — Return Routing Result
- Output: `english_text`, `source_language`, `detection_confidence`
- Calling workflow uses `source_language` to translate the response back before delivery

---

## Expected Outputs
```json
{
  "english_text": "What are the leave entitlements for public servants?",
  "source_language": "zu",
  "detection_confidence": 0.94,
  "language_name": "isiZulu"
}
```

---

## Edge Cases

| Situation | Action |
|-----------|--------|
| Language not in supported list | Respond in English, inform user |
| Detection confidence < 0.5 | Default to English, flag uncertainty |
| Code-switching (mixed languages in one query) | Detect dominant language, process in English |
| Empty or very short text (< 3 chars) | Skip detection, default to English |

---

## Known Issues & Notes

### Validated 2026-03-09 — Provider Research Complete
- **Translation provider selected: Google Cloud Translate**
  - 9/11 SA languages supported
  - `ve` (Tshivenda) and `nr` (isiNdebele) are NOT in Google Translate — fallback to English
  - Google uses ISO code `nso` for Sepedi (confirmed — do NOT use `sep`)
- **Tshivenda and isiNdebele gap:** No mainstream provider (Google, Azure, AWS) supports
  translation for these two languages. Options to revisit:
  - Lelapa AI (SA-based, focuses on indigenous languages) — evaluate when available
  - SADiLaR (South African Centre for Digital Language Resources) — research datasets
- [ ] Test detection accuracy for short SA language phrases (< 10 words)
- [ ] Confirm Azure Translator also supports `nso` code if used as fallback for translation
