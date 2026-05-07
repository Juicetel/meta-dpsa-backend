"""
Tool: followup_generator.py
Responsibility: Generate 2-3 contextually relevant follow-up questions
based on the current query and response. Helps users explore related topics.

WAT Role: Tools layer -- deterministic execution only.
Called by: query_handler.md (Step 10), demo/pipeline.py (Step 10)

Implementation: Template-based (no LLM required).
Selection:
  Position 1 always asks the user to narrow what they want to know about
  the matched topic (e.g. "What specifically do you want to know about
  annual leave?"). Positions 2-3 are the two most relevant template
  questions for that topic.

  Topic detection searches every category's keyword_trigger for the best
  overlap with query+response keywords. The chunk-derived `category` is
  only a tiebreaker, because the AWS retriever currently labels every
  chunk as "DPSA Document" (so dominant-category isn't a useful gate).

NOTE: Follow-up questions are generated in English internally and translated
by the calling workflow if the user's language is not English.
"""

import os
import re
from collections import Counter

MAX_FOLLOWUPS = int(os.getenv("MAX_FOLLOWUPS", "3"))

# Topic labels used in the "What specifically..." follow-up so it reads
# naturally for each topic (e.g. trigger "z83" -> "Form Z83").
_TOPIC_LABELS = {
    "z83": "Form Z83",
    "regulation": "Public Service Regulations",
    "performance": "performance management",
    "appointment": "appointments and recruitment",
    "contact": "DPSA contact details",
}

# Used when no specific trigger matched but the chunk category is known.
_CATEGORY_TOPIC_LABELS = {
    "benefits": "leave and benefits",
    "procedures": "DPSA procedures",
    "policies": "DPSA policies and regulations",
    "employment": "public service employment",
}

_FALLBACK_TOPIC_LABEL = "this topic"

# ── STOP WORDS ────────────────────────────────────────────────────────────────
_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "i", "me", "my",
    "do", "does", "did", "what", "how", "when", "where", "can", "please",
    "tell", "about", "get", "need", "want", "help", "for", "with",
    "in", "on", "of", "to", "and", "or", "not", "be", "been",
}

# ── TEMPLATE BANK ─────────────────────────────────────────────────────────────
# Structure: { category: { keyword_trigger: [questions], "default": [questions] } }
# keyword_trigger is a phrase (or word) matched against query+response keywords.
# "default" is the fallback when no trigger matches within a category.

_TEMPLATES = {
    "benefits": {
        "annual leave": [
            "How do I apply for annual leave through PERSAL?",
            "What happens to my unused annual leave if I resign?",
            "Can I take annual leave during my probation period?",
        ],
        "sick leave": [
            "What happens when my sick leave is exhausted?",
            "When do I need a medical certificate for sick leave?",
            "What is the difference between sick leave and incapacity leave?",
        ],
        "maternity": [
            "Does maternity leave affect my annual leave balance?",
            "Am I entitled to maternity leave if I am on a fixed-term contract?",
            "What is the procedure for notifying my department about my pregnancy?",
        ],
        "incapacity": [
            "How do I apply for temporary incapacity leave (TIL)?",
            "What medical evidence is required for an incapacity leave application?",
            "Who is the Health Risk Manager for the public service?",
        ],
        "family responsibility": [
            "Which family members qualify for family responsibility leave?",
            "How many days of family responsibility leave am I entitled to per year?",
            "What documents do I need when applying for family responsibility leave?",
        ],
        "leave without pay": [
            "Does leave without pay affect my pension contributions?",
            "What is the maximum period of leave without pay I can take?",
            "What are valid reasons for leave without pay to be approved?",
        ],
        "default": [
            "How do I check my leave balance on PERSAL?",
            "What is the difference between annual leave and sick leave?",
            "Who approves leave applications in my department?",
        ],
    },
    "procedures": {
        "z83": [
            "Where can I download the latest version of Form Z83?",
            "Do I still need to submit certified qualification copies with my Z83?",
            "What happens if my Z83 form is incomplete?",
        ],
        "grievance": [
            "How long does the grievance process take from start to finish?",
            "What happens if my grievance is not resolved at department level?",
            "Can I submit a grievance about a PERSAL salary error?",
        ],
        "appointment": [
            "Where is the Public Service Vacancy Circular published?",
            "How long must a government post be advertised before interviews?",
            "What security checks are done when I am appointed?",
        ],
        "default": [
            "Where can I find DPSA forms and application templates?",
            "How do I contact the DPSA for an enquiry?",
            "What is the Public Service Vacancy Circular and where do I find it?",
        ],
    },
    "policies": {
        "performance": [
            "When must my Performance Agreement be signed?",
            "How is the performance bonus calculated for public servants?",
            "What happens if my performance is rated as Unsatisfactory?",
        ],
        "regulation": [
            "Which employees are covered by the Public Service Regulations 2016?",
            "Where can I download the full text of the Public Service Regulations 2016?",
            "How do the 2016 Regulations differ from the 2001 Regulations?",
        ],
        "leave without pay": [
            "How long can I take leave without pay?",
            "Does leave without pay affect my pension?",
            "What are the steps to apply for leave without pay?",
        ],
        "default": [
            "Where can I find the Public Service Act?",
            "What is the PSCBC and what agreements does it cover?",
            "How do I find circulars and directives issued by DPSA?",
        ],
    },
    "employment": {
        "appointment": [
            "What qualifications are required to apply for a public service post?",
            "Can I apply for a post if I have a previous criminal record?",
            "How do I find current vacancies in the public service?",
        ],
        "contact": [
            "How do I contact the DPSA head office in Pretoria?",
            "What is the DPSA email address for general enquiries?",
            "What are the DPSA office hours?",
        ],
        "default": [
            "How do I apply for a job in the public service?",
            "What is PERSAL and why is it important for public servants?",
            "How do I verify that a job advertisement is official?",
        ],
    },
    "default": [
        "How do I find more information about DPSA policies and procedures?",
        "What forms are available on the DPSA website?",
        "How do I contact the DPSA for further assistance?",
    ],
}


def generate_followups(query: str, response: str, retrieved_chunks: list) -> list:
    """
    Generate 2-3 follow-up questions using template-based selection.

    Args:
        query:            The original English-language user query.
        response:         The English-language bot response.
        retrieved_chunks: List of chunk dicts returned by retriever/mock_retriever.

    Returns:
        List of up to MAX_FOLLOWUPS follow-up question strings in English.

    Raises:
        ValueError: If query or response is empty.
    """
    if not query or not query.strip():
        raise ValueError("query cannot be empty.")
    if not response or not response.strip():
        raise ValueError("response cannot be empty.")

    category = _dominant_category(retrieved_chunks)
    keywords = _extract_keywords(query + " " + response)
    topic_label, template_set = _select_template_set(category, keywords)

    specificity_question = f"What specifically do you want to know about {topic_label}?"
    return [specificity_question] + list(template_set[: max(MAX_FOLLOWUPS - 1, 0)])


def _extract_keywords(text: str) -> set:
    """Return a set of lowercase meaningful tokens from text."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return {t for t in text.split() if t not in _STOP_WORDS and len(t) > 2}


def _dominant_category(chunks: list) -> str:
    """Return the most common category value from retrieved chunks."""
    if not chunks:
        return "default"

    categories = [c.get("category", "default") for c in chunks]
    most_common = Counter(categories).most_common(1)[0][0]
    return most_common if most_common in _TEMPLATES else "default"


def _select_template_set(category: str, keywords: set) -> tuple:
    """
    Search every category's template bank for the keyword_trigger with the
    highest overlap with query+response keywords. Returns (topic_label,
    templates). The chunk-derived `category` is only used as a tiebreaker on
    equal overlap, since the AWS retriever currently labels every chunk as
    "DPSA Document" (so the dominant category isn't a reliable signal).
    Falls back to the matching category's "default" templates on no match.
    """
    best_overlap = 0
    best_in_dominant = False
    best_trigger = None
    best_templates = None

    for cat, bank in _TEMPLATES.items():
        if isinstance(bank, list):
            continue
        for trigger, templates in bank.items():
            if trigger == "default":
                continue
            trigger_tokens = set(trigger.lower().split())
            overlap = len(keywords & trigger_tokens)
            if overlap == 0:
                continue
            in_dominant = cat == category
            if (overlap, in_dominant) > (best_overlap, best_in_dominant):
                best_overlap = overlap
                best_in_dominant = in_dominant
                best_trigger = trigger
                best_templates = templates

    if best_trigger and best_templates is not None:
        topic_label = _TOPIC_LABELS.get(best_trigger, best_trigger)
        return (topic_label, best_templates)

    # No keyword match anywhere -- use the dominant category's default templates.
    category_bank = _TEMPLATES.get(category, _TEMPLATES["default"])
    if isinstance(category_bank, list):
        return (_FALLBACK_TOPIC_LABEL, category_bank)

    fallback_label = _CATEGORY_TOPIC_LABELS.get(category, _FALLBACK_TOPIC_LABEL)
    return (fallback_label, category_bank.get("default", _TEMPLATES["default"]))


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from tools.mock_retriever import retrieve

    test_cases = [
        ("How many annual leave days do I get?", "You are entitled to 22 working days...", "annual leave"),
        ("What is the sick leave policy?", "During a three-year cycle...", "sick leave"),
        ("How do I apply for a job?", "You must complete Form Z83...", "z83"),
    ]
    print("followup_generator.py -- smoke test\n")
    for query, response, topic in test_cases:
        chunks = retrieve(query, top_k=3)
        result = generate_followups(query, response, chunks)
        print(f"  Topic: {topic}")
        for q in result:
            print(f"    - {q}")
        print()
