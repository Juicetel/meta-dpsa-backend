"""
Tool: lang_detector.py
Responsibility: Detect the language of incoming text.
Returns ISO 639-1 code + confidence score.

Provider: Google Cloud Translation API v2 (detect endpoint)
Credentials: GOOGLE_APPLICATION_CREDENTIALS in .env

WAT Role: Tools layer — deterministic execution only.
Called by: query_handler.md (Step 3), language_router.md (Step 1)
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

# Recognised but not supported for translation — respond in English
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


def detect_language(text: str) -> dict:
    """
    Detect the language of the input text using Google Cloud Translation API.

    Args:
        text: The input string to detect language from.

    Returns:
        {
            "language": str,        # ISO 639-1 code (e.g. "zu")
            "confidence": float,    # 0.0 to 1.0
            "language_name": str,   # Human-readable name, or "Unknown" if not in our list
            "is_supported": bool    # True if language is in SUPPORTED_LANGUAGES
        }

    Raises:
        ValueError: If text is empty or None.
        RuntimeError: If the Google API call fails.
    """
    if not text or not text.strip():
        raise ValueError("Input text cannot be empty.")

    try:
        client = _get_client()
        result = client.detect_language(text)
    except Exception as e:
        raise RuntimeError(f"lang_detector.py: Google language detection failed: {e}")

    lang_code = result["language"]
    confidence = result["confidence"]

    all_languages = {**SUPPORTED_LANGUAGES, **UNSUPPORTED_LANGUAGES}
    language_name = all_languages.get(lang_code, "Unknown")
    is_supported = lang_code in SUPPORTED_LANGUAGES

    return {
        "language": lang_code,
        "confidence": confidence,
        "language_name": language_name,
        "is_supported": is_supported,
    }


if __name__ == "__main__":
    os.environ.setdefault(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "./google-credentials.json"
    )

    test_inputs = [
        "What are the leave entitlements for public servants?",          # English
        "Sawubona, ngicela usizo mayelana ne-DPSA.",                     # isiZulu
        "Wat is die verlofbeleide vir staatsamptenare?",                  # Afrikaans
        "Ditokelo tsa ho tlohela mosebetsi bakeng sa baahi ba mmuso.",   # Sesotho
        "Ke kopa thuso ka ditshwanelo tsa tiro ya mmuso.",               # Setswana
    ]

    print("lang_detector.py — live tests\n")
    for text in test_inputs:
        result = detect_language(text)
        supported = "OK" if result["is_supported"] else "NOT SUPPORTED"
        print(f"  [{result['language']} | conf: {result['confidence']:.2f} | {supported}] {text[:55]}")
