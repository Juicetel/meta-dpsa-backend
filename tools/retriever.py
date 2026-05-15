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
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

AWS_SEARCH_URL = os.getenv(
    "AWS_SEARCH_URL",
    "http://13.247.229.2:8000/api/documents/search/",
)
# Second AWS endpoint dedicated to www.dpsa.gov.za HTML pages
# (requested 2026-05-13, see workflows/aws_data_sync.md §8). Empty by
# default so the bot degrades cleanly to the combined-index endpoint
# until AWS delivers. Set in Render dashboard once the URL is known.
AWS_WEBPAGES_SEARCH_URL = os.getenv("AWS_WEBPAGES_SEARCH_URL", "")
MAX_RETRIEVAL_CHUNKS = int(os.getenv("MAX_RETRIEVAL_CHUNKS", "5"))
REQUEST_TIMEOUT = int(os.getenv("RETRIEVER_TIMEOUT", "10"))


def _retrieve_from(query: str, top_k: int, url: str, default_category: str) -> list:
    """
    Internal: POST {query, top_k} to an AWS search endpoint and convert
    the response into the bot's chunk dict shape. Used by both retrieve()
    (combined PDF+HTML index) and retrieve_webpages() (HTML-only index).
    """
    if query is None:
        raise ValueError("query cannot be None.")
    if not query.strip():
        return []

    k = top_k if top_k is not None else MAX_RETRIEVAL_CHUNKS

    payload = json.dumps({"query": query, "top_k": k}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"retriever.py: AWS API at {url} returned HTTP {e.code}: {e.reason}"
        )
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"retriever.py: Cannot reach AWS API at {url}: {e.reason}"
        )
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"retriever.py: Invalid JSON from AWS API at {url}: {e}"
        )

    raw_results = data.get("results", [])
    if not raw_results:
        return []

    chunks = []
    for i, item in enumerate(raw_results):
        # Real cosine similarity from the API; fall back to rank-based if missing
        if "similarity" in item:
            similarity_score = round(float(item["similarity"]), 3)
        else:
            raw_score: float = 1.0 - i * 0.05
            clamped: float = raw_score if raw_score >= 0.60 else 0.60
            similarity_score = int(clamped * 100) / 100.0

        # Clean display title -- strip file extensions
        raw_title = (
            item.get("title")
            or item.get("document_title")
            or item.get("section_title")
            or "DPSA Document"
        )
        for ext in (".pdf", ".PDF", ".docx", ".DOCX", ".doc", ".DOC"):
            raw_title = raw_title.replace(ext, "")
        source_title = raw_title.strip() or "DPSA Document"

        # Pick URL based on item type; new schema uses page_url for html, source_url for document
        item_type = item.get("type", "")
        if item_type == "html":
            source_url = item.get("page_url") or item.get("source_url", "")
        else:
            source_url = item.get("source_url") or item.get("page_url") or item.get("source_page_url", "")

        # URL-encode spaces and special chars in the path (e.g. "Annual Report.pdf")
        # First unquote to avoid double-encoding, then re-encode properly
        if source_url:
            parts = urlsplit(source_url)
            decoded_path = unquote(parts.path)
            source_url = urlunsplit((
                parts.scheme, parts.netloc,
                quote(decoded_path, safe="/"),
                parts.query, parts.fragment,
            ))

        # Infer doc_type from item type or URL extension
        if item_type == "html":
            doc_type = "webpage"
        else:
            url_lower = source_url.lower()
            if url_lower.endswith(".pdf"):
                doc_type = "pdf"
            elif url_lower.endswith((".doc", ".docx")):
                doc_type = "doc"
            else:
                doc_type = "webpage"

        # Capture the document's last-updated date so the LLM can prefer the
        # most recent version of a policy when multiple versions are retrieved.
        # AWS schema (aws_data_sync.md) lists scraped_at; tolerate common aliases.
        scraped_at = (
            item.get("scraped_at")
            or item.get("last_updated")
            or item.get("updated_at")
            or item.get("created_at")
            or item.get("date")
            or ""
        )

        chunks.append({
            "id": str(item.get("id", f"chunk_{i}")),
            "content": item.get("text", ""),
            "source_url": source_url,
            "source_title": source_title,
            "category": default_category,
            "doc_type": doc_type,
            "similarity_score": similarity_score,
            "scraped_at": scraped_at,
        })

    return chunks


def retrieve(query: str, top_k: int = None) -> list:
    """
    Retrieve from the combined PDFs + HTML index (existing AWS endpoint
    at AWS_SEARCH_URL). Returns top-k chunks ordered by similarity.

    Chunks are tagged `category="DPSA Document"`. See _retrieve_from for
    the full chunk dict shape.

    Raises:
        RuntimeError: On HTTP error or unreachable AWS endpoint.
        ValueError:   If query is None.
    """
    return _retrieve_from(query, top_k, AWS_SEARCH_URL, "DPSA Document")


def retrieve_webpages(query: str, top_k: int = None) -> list:
    """
    Retrieve from the dedicated www.dpsa.gov.za HTML index (second AWS
    endpoint at AWS_WEBPAGES_SEARCH_URL, requested 2026-05-13 per
    workflows/aws_data_sync.md §8).

    Returns [] when AWS_WEBPAGES_SEARCH_URL is unset so the bot degrades
    cleanly to the combined-index retriever before AWS delivers.

    Chunks are tagged `category="DPSA Webpage"` so the LLM can see they
    came from the dedicated HTML source.

    Raises:
        RuntimeError: On HTTP error or unreachable endpoint when the URL
                      IS set. (Empty URL is silent and returns [].)
        ValueError:   If query is None.
    """
    if not AWS_WEBPAGES_SEARCH_URL:
        return []
    return _retrieve_from(query, top_k, AWS_WEBPAGES_SEARCH_URL, "DPSA Webpage")


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
