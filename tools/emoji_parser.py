"""
Tool: emoji_parser.py
Responsibility: Detect emoji Unicode characters in query text and map them
to semantic meaning. Appends semantic context to the query string before
NLU processing.

WAT Role: Tools layer — deterministic execution only.
Called by: query_handler.md (Step 1)
"""

import re
import unicodedata

# Semantic map: emoji Unicode -> contextual meaning for DPSA queries
# Expand this map as patterns emerge from real usage logs
EMOJI_SEMANTIC_MAP = {
    # Documents & work
    "\U0001f4c4": "document",           # 📄
    "\U0001f4cb": "form or checklist",  # 📋
    "\U0001f4dd": "note or application",# 📝
    "\U0001f4bc": "work or briefcase",  # 💼
    "\U0001f4ca": "statistics or data", # 📊
    "\U0001f4c8": "progress or report", # 📈
    "\U0001f4c9": "decline or report",  # 📉
    # Communication
    "\U0001f4e7": "email",              # 📧
    "\U0001f4de": "phone call",         # 📞
    "\U0001f4ac": "question or chat",   # 💬
    "\u2753": "question",               # ❓
    "\u2754": "question",               # ❔
    # Actions
    "\U0001f50d": "search or inquiry",  # 🔍
    "\U0001f4e5": "application or submission", # 📥
    "\U0001f4e4": "submission",         # 📤
    # Sentiment / intent signals
    "\U0001f44d": "agreement or confirmation",   # 👍
    "\U0001f44e": "disagreement or rejection",   # 👎
    "\U0001f64f": "request or plea",             # 🙏
    "\u2705": "confirmed or completed",           # ✅
    "\u274c": "denied or problem",                # ❌
    "\u26a0\ufe0f": "warning or urgent",          # ⚠️
    # People / HR context
    "\U0001f468\u200d\U0001f4bc": "employee",    # 👨‍💼
    "\U0001f469\u200d\U0001f4bc": "employee",    # 👩‍💼
    "\U0001f91d": "agreement or partnership",    # 🤝
    # Money / benefits
    "\U0001f4b0": "salary or money",             # 💰
    "\U0001f4b3": "payment or card",             # 💳
    "\U0001f3e6": "banking or finance",          # 🏦
    # Leave / time
    "\U0001f3d6\ufe0f": "leave or vacation",     # 🏖️
    "\U0001f4c5": "date or schedule",            # 📅
    "\u23f0": "time or deadline",                # ⏰
}


def parse_emojis(query_text: str) -> dict:
    """
    Detect emoji Unicode characters in query text, map to semantic labels,
    and append semantic context to the query string before NLU processing.

    Args:
        query_text: Raw user message that may contain emoji characters.

    Returns:
        {
            "enriched_query": str,      # Original text + appended semantic context
            "detected_emojis": list,    # List of emoji characters found
            "emoji_meanings": list,     # Corresponding semantic labels
            "has_emojis": bool
        }

    Raises:
        ValueError: If query_text is None.
    """
    if query_text is None:
        raise ValueError("query_text cannot be None.")

    detected_emojis = []
    emoji_meanings = []

    for char in query_text:
        if char in EMOJI_SEMANTIC_MAP:
            detected_emojis.append(char)
            emoji_meanings.append(EMOJI_SEMANTIC_MAP[char])
        elif _is_emoji(char):
            # Emoji present but not in our map — note it without mapping
            detected_emojis.append(char)
            emoji_meanings.append("unknown_emoji")

    if emoji_meanings:
        unique_meanings = list(dict.fromkeys(m for m in emoji_meanings if m != "unknown_emoji"))
        if unique_meanings:
            context_suffix = " [context: " + ", ".join(unique_meanings) + "]"
            enriched_query = query_text + context_suffix
        else:
            enriched_query = query_text
    else:
        enriched_query = query_text

    return {
        "enriched_query": enriched_query,
        "detected_emojis": detected_emojis,
        "emoji_meanings": emoji_meanings,
        "has_emojis": bool(detected_emojis),
    }


def _is_emoji(char: str) -> bool:
    """Check if a character is an emoji using Unicode category."""
    try:
        return unicodedata.category(char) in ("So", "Sm") or ord(char) > 0x1F300
    except TypeError:
        return False


if __name__ == "__main__":
    tests = [
        "What is the 📋 for leave applications?",
        "I need help with my 💰 payment ❓",
        "No emojis here",
        "👍 that sounds good",
    ]
    for t in tests:
        result = parse_emojis(t)
        print(f"Input:    {t}")
        print(f"Enriched: {result['enriched_query']}")
        print(f"Emojis:   {result['detected_emojis']}")
        print(f"Meanings: {result['emoji_meanings']}\n")
