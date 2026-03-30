"""
Tool: retriever.py
Responsibility: Production retrieval from the AWS semantic search API.
Calls the AWS endpoint with the English query and returns top-k chunks
in the same schema as mock_retriever.py so the pipeline needs no other changes.

WAT Role: Tools layer -- deterministic execution only.
Called by: demo/pipeline.py (Step 6)

Endpoint: http://13.247.229.2:8000/api/documents/search/
Payload:  {"query": str, "top_k": int}
Corpus:   2605 DPSA documents + 133 website pages (semantic/vector search on AWS side)
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

AWS_SEARCH_URL = os.getenv(
    "AWS_SEARCH_URL",
    "http://13.247.229.2:8000/api/documents/search/",
)
MAX_RETRIEVAL_CHUNKS = int(os.getenv("MAX_RETRIEVAL_CHUNKS", "5"))
REQUEST_TIMEOUT = int(os.getenv("RETRIEVER_TIMEOUT", "10"))


def retrieve(query: str, top_k: int = None) -> list:
    """
    Call the AWS semantic search API and return top-k chunks.

    Args:
        query:  English-language query text.
        top_k:  Number of chunks to return. Defaults to MAX_RETRIEVAL_CHUNKS.

    Returns:
        List of chunk dicts ordered by relevance (ranked by API), each:
        {
            "id":               str,
            "content":          str,
            "source_url":       str,
            "source_title":     str,
            "category":         str,
            "doc_type":         str,   # "pdf" | "doc" | "webpage"
            "similarity_score": float, # rank-based estimate 0.60 - 1.00
        }
        Returns empty list if no results found.

    Raises:
        RuntimeError: On HTTP error or unreachable AWS endpoint.
        ValueError:   If query is None.
    """
    if query is None:
        raise ValueError("query cannot be None.")
    if not query.strip():
        return []

    k = top_k if top_k is not None else MAX_RETRIEVAL_CHUNKS

    payload = json.dumps({"query": query, "top_k": k}).encode("utf-8")
    req = urllib.request.Request(
        AWS_SEARCH_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"retriever.py: AWS API returned HTTP {e.code}: {e.reason}"
        )
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"retriever.py: Cannot reach AWS API at {AWS_SEARCH_URL}: {e.reason}"
        )
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"retriever.py: Invalid JSON from AWS API: {e}"
        )

    raw_results = data.get("results", [])
    if not raw_results:
        return []

    chunks = []
    for i, item in enumerate(raw_results):
        # Rank-based similarity score: 1.0 for first result, decreasing by 0.05 per rank
        raw_score: float = 1.0 - i * 0.05
        clamped: float = raw_score if raw_score >= 0.60 else 0.60
        rank_score: float = int(clamped * 100) / 100.0

        # Clean display title -- strip file extensions
        raw_title = (
            item.get("document_title")
            or item.get("section_title")
            or "DPSA Document"
        )
        for ext in (".pdf", ".PDF", ".docx", ".DOCX", ".doc", ".DOC"):
            raw_title = raw_title.replace(ext, "")
        source_title = raw_title.strip() or "DPSA Document"

        # Use direct document URL for citations; fall back to page URL
        source_url = item.get("source_url") or item.get("source_page_url", "")
        # URL-encode spaces and special chars in the path (e.g. "Annual Report.pdf")
        if source_url:
            parts = urlsplit(source_url)
            source_url = urlunsplit((
                parts.scheme, parts.netloc,
                quote(parts.path, safe="/"),
                parts.query, parts.fragment,
            ))

        # Infer doc_type from URL extension
        url_lower = source_url.lower()
        if url_lower.endswith(".pdf"):
            doc_type = "pdf"
        elif url_lower.endswith((".doc", ".docx")):
            doc_type = "doc"
        else:
            doc_type = "webpage"

        chunks.append({
            "id": str(item.get("id", f"chunk_{i}")),
            "content": item.get("text", ""),
            "source_url": source_url,
            "source_title": source_title,
            "category": "DPSA Document",
            "doc_type": doc_type,
            "similarity_score": rank_score,
        })

    return chunks


if __name__ == "__main__":
    test_queries = [
        "How many days of annual leave do I get?",
        "What is the sick leave policy?",
        "How do I apply for a government job?",
        "What is the grievance procedure?",
        "How do I apply for early retirement?",
    ]

    print("retriever.py -- live AWS API smoke test\n")
    print(f"Endpoint: {AWS_SEARCH_URL}\n")
    for q in test_queries:
        try:
            results = retrieve(q, top_k=3)
            print(f"  Query: {q[:60]}")
            if results:
                for r in results:
                    print(
                        f"    [{r['similarity_score']:.2f}] "
                        f"{r['source_title'][:55]}  ({r['doc_type']})"
                    )
            else:
                print("    No results -- would escalate")
        except RuntimeError as e:
            print(f"    ERROR: {e}")
        print()
