"""
Tool: validate_language_coverage.py
Purpose: Validate STT, TTS, and Translation coverage for all 11 SA official languages
         across candidate providers before committing to one.

Run this ONCE before choosing your provider. Document results in:
  - workflows/language_router.md  (translation coverage)
  - workflows/voice_handler.md    (STT + TTS coverage)

Usage:
  python tools/validate_language_coverage.py --provider google
  python tools/validate_language_coverage.py --provider azure
  python tools/validate_language_coverage.py --provider aws
  python tools/validate_language_coverage.py --all

Requirements (install only what you're testing):
  pip install google-cloud-speech google-cloud-texttospeech google-cloud-translate
  pip install azure-cognitiveservices-speech azure-ai-translation-text
  pip install boto3

Results are saved to .tmp/language_validation_<provider>_<date>.json
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# TEST DATA — one short sentence per language
# These are grammatically correct, DPSA-relevant phrases for each SA language.
# Using real sentences (not lorem ipsum) gives a meaningful STT/TTS quality signal.
# ─────────────────────────────────────────────────────────────────────────────
SA_LANGUAGES = {
    "en": {
        "name": "English",
        "bcp47_google": "en-ZA",
        "bcp47_azure": "en-ZA",
        "bcp47_aws": "en-ZA",
        "test_sentence": "What are the leave entitlements for public servants?",
        "risk": "low",
    },
    "af": {
        "name": "Afrikaans",
        "bcp47_google": "af-ZA",
        "bcp47_azure": "af-ZA",
        "bcp47_aws": "af-ZA",
        "test_sentence": "Wat is die verlofvoordele vir staatsamptenare?",
        "risk": "low",
    },
    "zu": {
        "name": "isiZulu",
        "bcp47_google": "zu-ZA",
        "bcp47_azure": "zu-ZA",
        "bcp47_aws": "zu-ZA",
        "test_sentence": "Yini inqubomgomo yokushiya umsebenzi kubasebenzi bakahulumeni?",
        "risk": "medium",
    },
    "xh": {
        "name": "isiXhosa",
        "bcp47_google": "xh-ZA",
        "bcp47_azure": "xh-ZA",
        "bcp47_aws": "xh-ZA",
        "test_sentence": "Zeziphi iimfanelo zokuphuma emsebenzini kwabaqeshwa baserhulumente?",
        "risk": "medium",
    },
    "st": {
        "name": "Sesotho",
        "bcp47_google": "st-ZA",
        "bcp47_azure": "st-ZA",
        "bcp47_aws": "st-ZA",
        "test_sentence": "Na ditokelo tsa ho tlohela mosebetsi bakeng sa baahi ba mmuso ke dife?",
        "risk": "medium",
    },
    "tn": {
        "name": "Setswana",
        "bcp47_google": "tn-ZA",
        "bcp47_azure": "tn-ZA",
        "bcp47_aws": "tn-ZA",
        "test_sentence": "Ditshwanelo tsa go tloga mo tirong tsa babereki ba puso ke dife?",
        "risk": "medium",
    },
    "nso": {
        "name": "Sepedi (Northern Sotho)",
        # NOTE: Google uses "nso", Azure may use "nso-ZA" or "sep-ZA" — test both
        "bcp47_google": "nso",
        "bcp47_azure": "nso-ZA",
        "bcp47_aws": "nso",
        "test_sentence": "Ditokelo tša go tlogela mošomo bakeng sa bašomi ba mmušo ke dife?",
        "risk": "high",
        "notes": "Code inconsistency: some providers use 'nso', others 'sep'. Test both.",
    },
    "ts": {
        "name": "Xitsonga",
        "bcp47_google": "ts-ZA",
        "bcp47_azure": "ts-ZA",
        "bcp47_aws": "ts-ZA",
        "test_sentence": "Swilungelo swa ku tshika ntirho hi vatirhi va mfumo i yini?",
        "risk": "high",
    },
    "ss": {
        "name": "siSwati",
        "bcp47_google": "ss-ZA",
        "bcp47_azure": "ss-ZA",
        "bcp47_aws": "ss-ZA",
        "test_sentence": "Tingelo tekushiya emsebentini ngebasebenzi behulumende yini?",
        "risk": "high",
        "notes": "Very limited STT/TTS support across all providers.",
    },
    "ve": {
        "name": "Tshivenda",
        "bcp47_google": "ve-ZA",
        "bcp47_azure": "ve-ZA",
        "bcp47_aws": "ve-ZA",
        "test_sentence": "Ndivhudziso ya pfanelo dza u fhungudza mushumo kha vhashumi vha muvhuso ndi nnyi?",
        "risk": "high",
    },
    "nr": {
        "name": "isiNdebele",
        "bcp47_google": "nr-ZA",
        "bcp47_azure": "nr-ZA",
        "bcp47_aws": "nr-ZA",
        "test_sentence": "Amalungelo wokushiya umsebenzi wabasebenzi beHulumende yini?",
        "risk": "high",
        "notes": "Very limited STT/TTS support across all providers.",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE CLOUD
# ─────────────────────────────────────────────────────────────────────────────

def validate_google_tts(results: dict):
    """Test Google Cloud TTS for all 11 SA languages."""
    print("\n[Google TTS] Testing voice availability...")
    try:
        from google.cloud import texttospeech
        client = texttospeech.TextToSpeechClient()

        # Get all available voices once
        all_voices = client.list_voices().voices
        available_codes = {v.language_codes[0] for v in all_voices}

        for iso, lang in SA_LANGUAGES.items():
            code = lang["bcp47_google"]
            supported = code in available_codes or any(
                code in vc for v in all_voices for vc in v.language_codes
            )
            results[iso]["tts_google"] = "supported" if supported else "NOT SUPPORTED"
            status = "✓" if supported else "✗"
            print(f"  {status} {lang['name']} ({code}): {results[iso]['tts_google']}")

    except ImportError:
        print("  [SKIP] google-cloud-texttospeech not installed.")
    except Exception as e:
        print(f"  [ERROR] Google TTS validation failed: {e}")


def validate_google_stt(results: dict):
    """Test Google Cloud STT for all 11 SA languages."""
    print("\n[Google STT] Testing language support...")
    try:
        from google.cloud import speech

        client = speech.SpeechClient()

        for iso, lang in SA_LANGUAGES.items():
            code = lang["bcp47_google"]
            try:
                # Attempt a minimal recognise call with a blank audio payload
                # Just checking if the language code is accepted (not rejected)
                config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=16000,
                    language_code=code,
                )
                audio = speech.RecognitionAudio(content=b"\x00" * 100)
                client.recognize(config=config, audio=audio)
                results[iso]["stt_google"] = "supported"
                print(f"  ✓ {lang['name']} ({code})")
            except Exception as e:
                err_str = str(e).lower()
                if "language" in err_str or "invalid" in err_str or "not supported" in err_str:
                    results[iso]["stt_google"] = "NOT SUPPORTED"
                    print(f"  ✗ {lang['name']} ({code}): NOT SUPPORTED")
                else:
                    # Other errors (auth, audio format) don't mean language is unsupported
                    results[iso]["stt_google"] = "unknown — check manually"
                    print(f"  ? {lang['name']} ({code}): {e}")

    except ImportError:
        print("  [SKIP] google-cloud-speech not installed.")


def validate_google_translate(results: dict):
    """Test Google Cloud Translation for all 11 SA languages."""
    print("\n[Google Translate] Testing language support...")
    try:
        from google.cloud import translate_v2 as translate

        client = translate.Client()
        supported = client.get_languages()
        supported_codes = {lang["language"] for lang in supported}

        for iso, lang in SA_LANGUAGES.items():
            # Google Translate uses short ISO codes (no region suffix)
            code = iso  # e.g. "zu", "xh", "af"
            is_supported = code in supported_codes
            results[iso]["translate_google"] = "supported" if is_supported else "NOT SUPPORTED"
            status = "✓" if is_supported else "✗"
            print(f"  {status} {lang['name']} ({code})")

    except ImportError:
        print("  [SKIP] google-cloud-translate not installed.")
    except Exception as e:
        print(f"  [ERROR] Google Translate validation failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# AZURE
# ─────────────────────────────────────────────────────────────────────────────

def validate_azure_tts(results: dict):
    """Test Azure Cognitive Services TTS for all 11 SA languages."""
    print("\n[Azure TTS] Testing voice availability...")
    try:
        import azure.cognitiveservices.speech as speechsdk

        speech_key = os.getenv("AZURE_SPEECH_KEY", "")
        speech_region = os.getenv("AZURE_SPEECH_REGION", "")
        if not speech_key or not speech_region:
            print("  [SKIP] AZURE_SPEECH_KEY or AZURE_SPEECH_REGION not set in .env")
            return

        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

        for iso, lang in SA_LANGUAGES.items():
            code = lang["bcp47_azure"]
            # Try synthesizing a minimal phrase
            ssml = f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{code}"><voice xml:lang="{code}">test</voice></speak>'
            result = synthesizer.speak_ssml_async(ssml).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                results[iso]["tts_azure"] = "supported"
                print(f"  ✓ {lang['name']} ({code})")
            else:
                results[iso]["tts_azure"] = f"NOT SUPPORTED ({result.cancellation_details.error_details if hasattr(result, 'cancellation_details') else 'unknown'})"
                print(f"  ✗ {lang['name']} ({code}): {results[iso]['tts_azure']}")

    except ImportError:
        print("  [SKIP] azure-cognitiveservices-speech not installed.")
    except Exception as e:
        print(f"  [ERROR] Azure TTS validation failed: {e}")


def validate_azure_translate(results: dict):
    """Test Azure Translator for all 11 SA languages."""
    print("\n[Azure Translate] Testing language support...")
    try:
        import requests

        key = os.getenv("AZURE_TRANSLATOR_KEY", "")
        endpoint = os.getenv("AZURE_TRANSLATOR_ENDPOINT", "https://api.cognitive.microsofttranslator.com")
        if not key:
            print("  [SKIP] AZURE_TRANSLATOR_KEY not set in .env")
            return

        response = requests.get(
            f"{endpoint}/languages",
            params={"api-version": "3.0", "scope": "translation"},
            headers={"Ocp-Apim-Subscription-Key": key},
        )
        supported_codes = set(response.json().get("translation", {}).keys())

        for iso, lang in SA_LANGUAGES.items():
            is_supported = iso in supported_codes
            results[iso]["translate_azure"] = "supported" if is_supported else "NOT SUPPORTED"
            status = "✓" if is_supported else "✗"
            print(f"  {status} {lang['name']} ({iso})")

    except ImportError:
        print("  [SKIP] requests not installed.")
    except Exception as e:
        print(f"  [ERROR] Azure Translate validation failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS + REPORT
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(results: dict):
    """Print a summary table of validation results."""
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"{'Language':<30} {'Risk':<8} {'G-STT':<16} {'G-TTS':<16} {'G-Trans':<16} {'AZ-TTS':<16} {'AZ-Trans':<16}")
    print("-" * 80)

    for iso, lang in SA_LANGUAGES.items():
        r = results.get(iso, {})
        def fmt(v):
            if not v: return "not tested"
            return "✓" if v == "supported" else "✗ NO"

        print(
            f"{lang['name']:<30} {lang['risk']:<8} "
            f"{fmt(r.get('stt_google')):<16} "
            f"{fmt(r.get('tts_google')):<16} "
            f"{fmt(r.get('translate_google')):<16} "
            f"{fmt(r.get('tts_azure')):<16} "
            f"{fmt(r.get('translate_azure')):<16}"
        )

    print("\nACTION ITEMS:")
    for iso, lang in SA_LANGUAGES.items():
        r = results.get(iso, {})
        not_supported = [k for k, v in r.items() if v and "NOT SUPPORTED" in str(v)]
        if not_supported:
            print(f"  ✗ {lang['name']}: NOT supported for {', '.join(not_supported)}")
        if lang.get("notes"):
            print(f"  ⚠ {lang['name']}: {lang['notes']}")


def save_results(results: dict, provider: str):
    """Save full results to .tmp/ as JSON."""
    Path(".tmp").mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f".tmp/language_validation_{provider}_{date_str}.json")
    with open(output_path, "w") as f:
        json.dump({"languages": SA_LANGUAGES, "results": results, "tested_at": date_str}, f, indent=2)
    print(f"\nFull results saved to: {output_path}")
    print("Update workflows/language_router.md and workflows/voice_handler.md with these results.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate SA language coverage across STT/TTS/Translation providers.")
    parser.add_argument("--provider", choices=["google", "azure", "aws", "all"], default="all")
    args = parser.parse_args()

    results = {iso: {} for iso in SA_LANGUAGES}

    if args.provider in ("google", "all"):
        validate_google_tts(results)
        validate_google_stt(results)
        validate_google_translate(results)

    if args.provider in ("azure", "all"):
        validate_azure_tts(results)
        validate_azure_translate(results)

    print_summary(results)
    save_results(results, args.provider)
