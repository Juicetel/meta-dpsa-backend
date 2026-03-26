"""
Tool: translator.py
Responsibility: Translate text between English and all 11 SA official languages.
Used for both query translation (to English) and response translation (to user language).

Provider: Google Cloud Translation API v2
Credentials: GOOGLE_APPLICATION_CREDENTIALS in .env

WAT Role: Tools layer — deterministic execution only.
Called by: query_handler.md (Steps 4, 9), language_router.md (Step 4)
"""

import json
import os

from google.cloud import translate_v2 as translate
from google.oauth2 import service_account

# Languages with Google Translate support (validated 2026-03-09)
SUPPORTED_LANGUAGES = {
    "en": "English",
    "af": "Afrikaans",
    "zu": "isiZulu",
    "xh": "isiXhosa",
    "nso": "Sepedi (Northern Sotho)",
    "tn": "Setswana",
    "st": "Sesotho",
    "ts": "Xitsonga",
    "ss": "siSwati",
}

# Not supported by Google Translate — fallback to English
UNSUPPORTED_LANGUAGES = {
    "ve": "Tshivenda",
    "nr": "isiNdebele",
}

_client = None


def _get_client():
    """Return a cached Google Translate client.

    Supports two credential methods:
    - GOOGLE_CREDENTIALS_JSON env var: full service-account JSON as a string (used on Render/cloud)
    - GOOGLE_APPLICATION_CREDENTIALS env var: path to a credentials file (used locally)
    """
    global _client
    if _client is None:
        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if creds_json:
            info = json.loads(creds_json)
            creds = service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/cloud-translation"],
            )
            _client = translate.Client(credentials=creds)
        else:
            _client = translate.Client()
    return _client


def translate_text(text: str, source_lang: str, target_lang: str) -> dict:
    """
    Translate text from source_lang to target_lang.

    Args:
        text:        The text to translate.
        source_lang: ISO 639-1 source language code (e.g. "zu").
        target_lang: ISO 639-1 target language code (e.g. "en").

    Returns:
        {
            "translated_text": str,
            "source_lang": str,
            "target_lang": str,
        }

    Raises:
        ValueError: If text is empty or a language code is unsupported.
        RuntimeError: If the Google Translate API call fails.
    """
    if not text or not text.strip():
        raise ValueError("Input text cannot be empty.")

    all_languages = {**SUPPORTED_LANGUAGES, **UNSUPPORTED_LANGUAGES}

    if source_lang not in all_languages:
        raise ValueError(f"Unknown source language code: '{source_lang}'")

    if target_lang not in all_languages:
        raise ValueError(f"Unknown target language code: '{target_lang}'")

    if source_lang in UNSUPPORTED_LANGUAGES or target_lang in UNSUPPORTED_LANGUAGES:
        unsupported = source_lang if source_lang in UNSUPPORTED_LANGUAGES else target_lang
        raise ValueError(
            f"'{unsupported}' ({UNSUPPORTED_LANGUAGES[unsupported]}) is not supported "
            f"by Google Translate. Fallback to English should be handled by the calling workflow."
        )

    # Short-circuit: no translation needed
    if source_lang == target_lang:
        return {
            "translated_text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
        }

    try:
        client = _get_client()
        result = client.translate(
            text,
            source_language=source_lang,
            target_language=target_lang,
        )
        return {
            "translated_text": result["translatedText"],
            "source_lang": source_lang,
            "target_lang": target_lang,
        }
    except Exception as e:
        raise RuntimeError(f"translator.py: Google Translate API call failed: {e}")


if __name__ == "__main__":
    os.environ.setdefault(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "./google-credentials.json"
    )

    test_cases = [
        ("What are the leave entitlements for public servants?", "en", "zu"),
        ("What are the leave entitlements for public servants?", "en", "af"),
        ("What are the leave entitlements for public servants?", "en", "nso"),
        ("Sawubona, ngicela usizo nge-DPSA.", "zu", "en"),
    ]

    print("translator.py — live tests\n")
    for text, src, tgt in test_cases:
        result = translate_text(text, src, tgt)
        print(f"  [{src} -> {tgt}] {result['translated_text']}")
