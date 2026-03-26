"""
Tool: mock_retriever.py
Responsibility: Demo stand-in for retriever.py.
Loads demo/dpsa_knowledge.json and uses keyword frequency scoring to
simulate vector similarity search. Returns top-k chunks in the same
format that retriever.py will return when pgvector is available.

WAT Role: Tools layer -- deterministic execution only.
Called by: demo/pipeline.py (Step 6, stand-in for query_handler.md)

SWAP TO PRODUCTION:
  In demo/pipeline.py, change:
    from tools.mock_retriever import retrieve
  to:
    from tools.retriever import retrieve
  when pgvector credentials are available from the AWS team.
"""

import json
import os
import re
from pathlib import Path

KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "demo" / "dpsa_knowledge.json"
MAX_RETRIEVAL_CHUNKS = int(os.getenv("MAX_RETRIEVAL_CHUNKS", "5"))

_knowledge_base: list = []

# ── STOP WORDS ─────────────────────────────────────────────────────────────────
_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "i", "me", "my", "we", "our",
    "you", "your", "he", "she", "it", "they", "them", "their",
    "this", "that", "these", "those", "what", "which", "who", "how",
    "when", "where", "why", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "and", "or", "but", "not", "no", "so", "if", "then",
    "than", "as", "about", "get", "please", "help", "tell", "know",
    "want", "need", "use",
    # Domain-boilerplate: appear in virtually every DPSA chunk, carry no topical signal
    "south", "africa", "african", "public", "service", "government", "department",
    "dpsa", "employee", "employees", "employer", "servant", "servants", "official",
}

# ── SYNONYM EXPANSION ──────────────────────────────────────────────────────────
# Maps common query vocabulary to the terms used in dpsa_knowledge.json.
_SYNONYMS = {
    "vacation":            ["annual leave", "leave cycle"],
    "holiday":             ["annual leave"],
    "days off":            ["annual leave", "leave"],
    "time off":            ["annual leave", "leave"],
    "ill":                 ["sick", "medical", "incapacity"],
    "ill health":          ["sick leave", "incapacity"],
    "illness":             ["sick leave", "medical"],
    "doctor":              ["medical certificate", "sick leave"],
    "pregnancy":           ["maternity", "maternity leave"],
    "baby":                ["maternity", "birth"],
    "pregnant":            ["maternity leave"],
    "job":                 ["employment", "appointment", "vacancy"],
    "jobs":                ["employment", "vacancy", "appointment"],
    "apply":               ["application", "z83", "form"],
    "application":         ["z83", "form", "vacancy"],
    "form":                ["z83", "application form"],
    "complain":            ["grievance"],
    "complaint":           ["grievance procedure"],
    "dispute":             ["grievance", "bargaining council"],
    "unpaid":              ["leave without pay", "lwop"],
    "salary":              ["remuneration", "pay", "persal"],
    "pay":                 ["remuneration", "salary"],
    "appraisal":           ["performance management", "pmds"],
    "review":              ["performance", "pmds"],
    "rating":              ["performance management", "pmds", "assessment"],
    "assessment":          ["performance", "pmds"],
    "bonus":               ["performance bonus", "highly effective"],
    "death":               ["family responsibility", "bereavement"],
    "funeral":             ["family responsibility leave"],
    "bereavement":         ["family responsibility leave"],
    "child":               ["family responsibility", "maternity"],
    "contact":             ["dpsa contact", "head office", "email"],
    "address":             ["dpsa contact", "pretoria", "head office"],
    "phone":               ["switchboard", "contact"],
    "email":               ["contact", "info@dpsa"],
    "regulation":          ["public service regulations", "psr"],
    "regulations":         ["public service regulations", "2016"],
    "persal":              ["persal", "hr system"],
    "exhausted":           ["incapacity", "temporary incapacity"],
    "tired":               ["sick leave"],
    "injury":              ["incapacity leave", "sick leave"],
    "probation":           ["appointment", "conditions"],
    "fired":               ["dismissal", "discipline"],
    "dismissed":           ["dismissal", "discipline"],
    "resign":              ["resignation", "annual leave"],
    "hire":                ["appointment", "recruitment"],
    "hired":               ["appointment", "vacancy"],
    "advertise":           ["vacancy circular", "advertisement"],
    "advert":              ["vacancy circular", "advertisement"],
    "interview":           ["shortlisting", "appointment"],
    "cv":                  ["z83", "application form"],
    "certificate":         ["medical certificate", "qualifications"],
    "qualifications":      ["z83", "appointment", "shortlisted"],
    "entitlement":         ["annual leave", "sick leave", "benefits"],
    "entitlements":        ["annual leave", "sick leave", "benefits"],
    "allowance":           ["benefits", "conditions of service"],
    "benefits":            ["leave", "pension", "conditions of service"],
    "policy":              ["public service regulations", "leave policy"],
    "policies":            ["public service regulations", "dpsa"],
    "rule":                ["regulation", "policy"],
    "rules":               ["regulations", "policy"],
}


def retrieve(query: str, top_k: int = None) -> list:
    """
    Simulate vector similarity retrieval using keyword frequency scoring.

    Args:
        query:  English-language query text.
        top_k:  Number of chunks to return. Defaults to MAX_RETRIEVAL_CHUNKS.

    Returns:
        List of chunk dicts ordered by relevance score (descending), matching
        the retriever.py return schema:
        [
            {
                "id": str,
                "content": str,
                "source_url": str,
                "source_title": str,
                "category": str,
                "doc_type": str,
                "scraped_at": str,
                "similarity_score": float   # normalised 0.0 to 1.0
            },
            ...
        ]
        Returns empty list if no keyword matches are found.

    Raises:
        ValueError: If query is None.
        RuntimeError: If the knowledge base file cannot be loaded.
    """
    if query is None:
        raise ValueError("query cannot be None.")
    if not query.strip():
        return []

    k = top_k if top_k is not None else MAX_RETRIEVAL_CHUNKS
    chunks = _load_knowledge_base()
    scored = _score_chunks(query, chunks)

    matched = [(score, chunk) for score, chunk in scored if score > 0.0]
    if not matched:
        return []

    matched.sort(key=lambda x: x[0], reverse=True)
    top = matched[:k]

    results = []
    for score, chunk in top:
        result = dict(chunk)
        result["similarity_score"] = round(score, 4)
        results.append(result)

    return results


def _tokenise(text: str) -> list:
    """Lowercase, strip punctuation, split, remove stop words."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


def _expand_query(tokens: list) -> list:
    """Add synonym expansions to the token list."""
    expanded = list(tokens)
    for token in tokens:
        if token in _SYNONYMS:
            expansion = _SYNONYMS[token]
            if isinstance(expansion, list):
                expanded.extend(expansion)
            else:
                expanded.append(expansion)
    # Bigram synonyms
    for i in range(len(tokens) - 1):
        bigram = tokens[i] + " " + tokens[i + 1]
        if bigram in _SYNONYMS:
            expanded.extend(_SYNONYMS[bigram])
    return expanded


def _score_chunks(query: str, chunks: list) -> list:
    """
    Score each chunk against the query.
    Title match weighted 1.5x, body match 1.0x.
    Normalised to 0-1 range (capped).
    """
    tokens = _tokenise(query)
    expanded = _expand_query(tokens)

    # Deduplicate while preserving order
    seen = set()
    query_terms = []
    for t in expanded:
        if t not in seen:
            seen.add(t)
            query_terms.append(t)

    if not query_terms:
        return [(0.0, chunk) for chunk in chunks]

    scored = []
    for chunk in chunks:
        body  = chunk["content"].lower()
        title = chunk["source_title"].lower()

        match_count = 0.0
        for term in query_terms:
            if term in title:
                match_count += 1.5
            elif term in body:
                match_count += 1.0

        raw_score = match_count / len(query_terms)
        score = min(raw_score, 1.0)
        scored.append((score, chunk))

    return scored


def _load_knowledge_base() -> list:
    """Load and cache the knowledge base JSON."""
    global _knowledge_base
    if _knowledge_base:
        return _knowledge_base
    try:
        with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _knowledge_base = data["chunks"]
        return _knowledge_base
    except FileNotFoundError:
        raise RuntimeError(
            f"mock_retriever.py: Knowledge base not found at {KNOWLEDGE_BASE_PATH}. "
            "Ensure demo/dpsa_knowledge.json exists."
        )
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"mock_retriever.py: Failed to parse knowledge base: {e}")


if __name__ == "__main__":
    test_queries = [
        "How many days of annual leave do I get?",
        "What is the sick leave policy?",
        "How do I apply for a government job?",
        "What is the grievance procedure?",
        "I need maternity leave information",
        "What is the GDP of South Africa?",   # Should return no results
    ]

    print("mock_retriever.py -- smoke test\n")
    for q in test_queries:
        results = retrieve(q, top_k=3)
        print(f"  Query: {q[:60]}")
        if results:
            for r in results:
                print(f"    [{r['similarity_score']:.3f}] {r['source_title'][:60]}")
        else:
            print("    No results -- would escalate")
        print()
