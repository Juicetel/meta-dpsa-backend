"""
Tool: stt_transcriber.py
Responsibility: Transcribe voice input audio to text in the detected or selected SA language.
Returns transcript text and confidence score.

*** PHASE 2 — DO NOT IMPLEMENT UNTIL PHASE 2 BEGINS ***
The bot is text-to-text for Phase 1. This tool is preserved for planning only.

WAT Role: Tools layer — deterministic execution only.
Called by: voice_handler.md (Step 1)
"""

import os
from pathlib import Path

STT_PROVIDER = os.getenv("STT_PROVIDER", "")  # "google_cloud" | "azure" | "aws_transcribe"

SUPPORTED_LANGUAGES = {
    "en": "English",
    "zu": "isiZulu",
    "xh": "isiXhosa",
    "af": "Afrikaans",
    "nso": "Sepedi (Northern Sotho)",
    "tn": "Setswana",
    "st": "Sesotho",
    "ts": "Xitsonga",
    "ss": "siSwati",
    "ve": "Tshivenda",
    "nr": "isiNdebele",
}

SUPPORTED_FORMATS = {"wav", "mp3", "ogg", "flac", "m4a"}


def transcribe(audio_file, language_hint: str = None) -> dict:
    """
    Transcribe an audio file to text.

    Args:
        audio_file:     File path (str/Path) or raw bytes of the audio.
        language_hint:  ISO 639-1 code if the user selected a language in the UI.
                        Passed to the STT provider to improve accuracy.

    Returns:
        {
            "transcript": str,
            "confidence": float,        # 0.0 to 1.0
            "detected_language": str,   # ISO code returned by STT provider
            "duration_seconds": float
        }

    Raises:
        ValueError: If audio_file is None or format is unsupported.
        RuntimeError: If the STT API call fails.

    IMPORTANT: If confidence < STT_CONFIDENCE_THRESHOLD (from .env, default 0.75),
    the voice_handler.md workflow will prompt the user to repeat or switch to text.
    Do NOT process low-confidence transcripts.

    TODO: Select and integrate an STT provider.
    CRITICAL: Validate all 11 SA language ISO codes before choosing a provider.
    Options:
    - Google Cloud Speech-to-Text — validate SA language BCP-47 codes
    - Azure Cognitive Services Speech — validate SA language locale codes
    - AWS Transcribe — validate SA language support (limited for some SA languages)
    Document validated languages in voice_handler.md Known Issues.
    """
    if audio_file is None:
        raise ValueError("audio_file cannot be None.")

    if isinstance(audio_file, (str, Path)):
        ext = Path(str(audio_file)).suffix.lstrip(".").lower()
        if ext not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported audio format: .{ext}. "
                f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
            )

    if language_hint and language_hint not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language hint: {language_hint}")

    # TODO: Replace this stub with actual provider call
    # Example (Google Cloud):
    # from google.cloud import speech
    # client = speech.SpeechClient()
    # config = speech.RecognitionConfig(
    #     language_code=language_hint or "en-ZA",
    #     alternative_language_codes=[...],
    # )
    # response = client.recognize(config=config, audio=audio)
    # result = response.results[0].alternatives[0]
    # return {"transcript": result.transcript, "confidence": result.confidence, ...}

    raise NotImplementedError(
        "stt_transcriber.py: STT provider not yet configured. "
        f"STT_PROVIDER env var is: '{STT_PROVIDER}'. "
        "See voice_handler.md Known Issues for provider validation checklist."
    )


if __name__ == "__main__":
    print("stt_transcriber.py — provider not yet configured.")
    print(f"Set STT_PROVIDER in .env. Current value: '{STT_PROVIDER}'")
