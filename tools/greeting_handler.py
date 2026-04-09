"""
Tool: greeting_handler.py
Responsibility: Detect if user input is a greeting and generate appropriate welcome response
with language selection options.

WAT Role: Tools layer -- deterministic execution only.
Called by: demo/pipeline.py (Step 2b - greeting detection)
"""

import re
from tools.lang_detector import SUPPORTED_LANGUAGES


def is_language_selection(query: str) -> tuple:
    """
    Check if user input is a language selection response.

    Args:
        query: User input text

    Returns:
        Tuple of (is_selection: bool, language_code: str | None)
    """
    if not query or len(query.strip()) == 0:
        return (False, None)

    query_clean = query.strip().lower()

    # Check if query matches any supported language name or code
    for code, name in SUPPORTED_LANGUAGES.items():
        # Match full name or code
        if query_clean == name.lower() or query_clean == code.lower():
            return (True, code)
        # Match main name without parentheses (e.g., "sepedi" matches "Sepedi (Northern Sotho)")
        name_main = name.split('(')[0].strip().lower()
        if query_clean == name_main:
            return (True, code)

    return (False, None)


# Common greetings across all SA languages
GREETING_PATTERNS = [
    # English
    r'\b(hi|hello|hey|howdy|greetings|good morning|good afternoon|good evening)\b',
    # Afrikaans
    r'\b(hallo|goeiemore|goeie more|goeiedag|goeie dag|goeiemiddag|goeie middag)\b',
    # isiZulu
    r'\b(sawubona|sanibonani|yebo|ngiyabonga)\b',
    # isiXhosa
    r'\b(molo|molweni|mholo)\b',
    # Sepedi
    r'\b(dumela|thobela|dumelang)\b',
    # Setswana
    r'\b(dumela|dumelang)\b',
    # Sesotho
    r'\b(dumela|dumelang|lumela)\b',
    # Xitsonga
    r'\b(avuxeni|xewani|ahee)\b',
    # siSwati
    r'\b(sawubona|sanibonani|yebo)\b',
]


def is_greeting(query: str) -> bool:
    """
    Check if the user input is a greeting.

    Args:
        query: User input text

    Returns:
        True if the query matches greeting patterns, False otherwise
    """
    if not query or len(query.strip()) == 0:
        return False

    query_lower = query.lower().strip()

    # Remove punctuation for matching
    query_clean = re.sub(r'[^\w\s]', '', query_lower)

    # Check if query is very short (likely a greeting)
    word_count = len(query_clean.split())
    if word_count <= 3:
        for pattern in GREETING_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return True

    return False


def generate_greeting_response(detected_language: str = "en") -> dict:
    """
    Generate a welcome message with language selection options.

    Args:
        detected_language: ISO 639-1 language code detected from greeting

    Returns:
        dict with greeting response structure:
        {
            "is_greeting": True,
            "response": str,  # Greeting message in detected language
            "language_options": list[dict],  # Available language choices
            "detected_language": str
        }
    """

    # Brief greeting (just welcome)
    greetings = {
        "en": "Hello! Welcome to Batho Pele AI.",
        "af": "Hallo! Welkom by Batho Pele AI.",
        "zu": "Sawubona! Wamukelekile ku-Batho Pele AI.",
        "xh": "Molo! Wamkelekile kwi-Batho Pele AI.",
        "nso": "Thobela! Re go amogela go Batho Pele AI.",
        "tn": "Dumelang! Re go amogela kwa Batho Pele AI.",
        "st": "Lumela! Re u amohela ho Batho Pele AI.",
        "ts": "Avuxeni! Mi amukeriwa eka Batho Pele AI.",
        "ss": "Sawubona! Wemukelekile ku-Batho Pele AI.",
    }

    language_prompt = {
        "en": "\n\nWhich language would you like to use?",
        "af": "\n\nWatter taal wil jy gebruik?",
        "zu": "\n\nUfuna ukusebenzisa luluphi ulimi?",
        "xh": "\n\nUfuna ukusebenzisa luluphi ulwimi?",
        "nso": "\n\nO nyaka go šomiša polelo efe?",
        "tn": "\n\nO batla go dirisa puo efe?",
        "st": "\n\nO batla ho sebedisa puo efe?",
        "ts": "\n\nU lava ku tirhisa ririmi rihi?",
        "ss": "\n\nUfuna kusebentisa lulwimi loluluphina?",
    }

    # Use English as fallback if detected language not supported
    lang = detected_language if detected_language in greetings else "en"

    # Build greeting message (just greeting + language selection prompt)
    greeting_text = greetings[lang]
    prompt_text = language_prompt[lang]

    full_response = f"{greeting_text}{prompt_text}"

    # Build language options list
    language_options = []
    for code, name in SUPPORTED_LANGUAGES.items():
        language_options.append({
            "code": code,
            "name": name,
            "label": f"{name} ({code})"
        })

    return {
        "is_greeting": True,
        "response": full_response,
        "language_options": language_options,
        "detected_language": lang,
        "confidence": 1.0
    }


def generate_language_confirmation(selected_language: str) -> dict:
    """
    Generate a confirmation message after language selection.

    Args:
        selected_language: ISO 639-1 language code selected by user

    Returns:
        dict with confirmation message:
        {
            "response": str,  # Confirmation in selected language
            "language": str   # Selected language code
        }
    """
    confirmations = {
        "en": "Great! I'll assist you in English.\n\nHow can I help you today?",
        "af": "Goed! Ek sal jou in Afrikaans help.\n\nHoe kan ek jou vandag help?",
        "zu": "Kuhle! Ngizokusiza ngesiZulu.\n\nNgingakusiza kanjani namhlanje?",
        "xh": "Kuhle! Ndiza kukunceda ngesiXhosa.\n\nNdingakunceda njani namhlanje?",
        "nso": "Go botse! Ke tla go thuša ka Sepedi.\n\nNka go thuša bjang lehono?",
        "tn": "Go siame! Ke tla go thusa ka Setswana.\n\nNka go thusa jang gompieno?",
        "st": "Ho lokile! Ke tla u thusa ka Sesotho.\n\nNka u thusa joang kajeno?",
        "ts": "Ku hanya! Ndzi ta ku pfuna hi Xitsonga.\n\nNdzi nga ku pfuna njhani namuntlha?",
        "ss": "Kuhle! Ngitakusita ngeSiswati.\n\nNgingakusita kanjani lalelilanga?",
    }

    lang = selected_language if selected_language in confirmations else "en"

    return {
        "response": confirmations[lang],
        "language": lang
    }


if __name__ == "__main__":
    # Test greeting detection
    test_cases = [
        "Hello",
        "Hi there",
        "Sawubona",
        "Dumela",
        "Goeiemore",
        "How do I apply for leave?",  # Not a greeting
        "Molo",
        "Hey",
    ]

    print("greeting_handler.py -- smoke test\n")
    for test in test_cases:
        is_greet = is_greeting(test)
        print(f"'{test}' → Greeting: {is_greet}")
        if is_greet:
            result = generate_greeting_response("en")
            print(f"  Response preview: {result['response'][:80]}...")
            print(f"  Languages offered: {len(result['language_options'])}")
        print()
