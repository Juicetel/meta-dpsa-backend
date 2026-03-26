"""
Tool: followup_generator.py
Responsibility: Generate 2-3 contextually relevant follow-up questions
based on the current query and response. Helps users explore related topics.

WAT Role: Tools layer -- deterministic execution only.
Called by: query_handler.md (Step 10), demo/pipeline.py (Step 10)

Implementation: Template-based (no LLM required).
Two-layer selection:
  Layer 1: Dominant category from retrieved_chunks (benefits / procedures / policies / employment)
  Layer 2: Keyword refinement within category to pick the most relevant template set.

NOTE: Follow-up questions are generated in English internally and translated
by the calling workflow if the user's language is not English.
"""

import os
import re
from collections import Counter

MAX_FOLLOWUPS = int(os.getenv("MAX_FOLLOWUPS", "3"))

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
    template_set = _select_template_set(category, keywords)

    return template_set[:MAX_FOLLOWUPS]


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


def _select_template_set(category: str, keywords: set) -> list:
    """
    Within a category's template bank, find the keyword_trigger with
    maximum overlap with query+response keywords. Return its template list.
    Falls back to the category "default" if no trigger matches.
    """
    category_bank = _TEMPLATES.get(category, _TEMPLATES["default"])

    if isinstance(category_bank, list):
        return category_bank

    best_trigger = None
    best_overlap = 0

    for trigger, templates in category_bank.items():
        if trigger == "default":
            continue
        trigger_tokens = set(trigger.lower().split())
        overlap = len(keywords & trigger_tokens)
        if overlap > best_overlap:
            best_overlap = overlap
            best_trigger = trigger

    if best_trigger and best_overlap > 0:
        return category_bank[best_trigger]

    return category_bank.get("default", _TEMPLATES["default"])


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
