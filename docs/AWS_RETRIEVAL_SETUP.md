# AWS Semantic Search API Setup Guide

This document explains how the DPSA Bot connects to the AWS Semantic Search API for document retrieval.

## Overview

The DPSA Bot uses a dedicated AWS-hosted semantic search endpoint to retrieve relevant DPSA documents based on user queries. The AWS team manages:
- **Document corpus**: 2,605 DPSA documents + 133 website pages
- **Vector embeddings**: Semantic search using pre-computed embeddings
- **Search API**: HTTP endpoint for querying the knowledge base

## Architecture

```
User Query → Language Detection → Translation to English
    ↓
AWS Semantic Search API (http://13.247.229.2:8000/api/documents/search/)
    ↓
Top-K Relevant Chunks Retrieved → LLM Generation → Translation Back
    ↓
Response to User
```

## Endpoint Configuration

### API Endpoint
```
http://13.247.229.2:8000/api/documents/search/
```

### Request Format
```json
{
  "query": "public service recruitment guidelines South Africa",
  "top_k": 5
}
```

### Response Format
```json
{
  "query": "public service recruitment guidelines South Africa",
  "count": 5,
  "results": [
    {
      "id": 31565,
      "document_id": 1826,
      "document_title": "Circular 04 (click here to view the full document)",
      "source_url": "https://www.dpsa.gov.za/dpsa2g/documents/vacancies/2026/PSV%20CIRCULAR%2004%20of%202026.pdf",
      "source_page_url": "https://www.dpsa.gov.za/newsroom/psvc/circular-04-of-2026/",
      "chunk_index": 111,
      "section_title": "",
      "page_number": null,
      "text": "The Office of the Public Service Commission (OPSC)...",
      "similarity": 0.8079134936384279
    }
  ]
}
```

## Local Configuration

### Environment Variable

Add to your `.env` file:
```env
AWS_SEARCH_URL=http://13.247.229.2:8000/api/documents/search/
MAX_RETRIEVAL_CHUNKS=5
RETRIEVER_TIMEOUT=10
```

### Tool Implementation

The retriever is implemented in [tools/retriever.py](../tools/retriever.py):

```python
def retrieve(query: str, top_k: int = None) -> list:
    """
    Call the AWS semantic search API and return top-k chunks.

    Args:
        query:  English-language query text.
        top_k:  Number of chunks to return (default: 5)

    Returns:
        List of chunk dicts with content, source_url, source_title, etc.
    """
```

## Testing the Endpoint

### Quick Test (Python)
```bash
cd "c:\Users\Thato Molaba\Documents\DPSA Bot"
python tools/retriever.py
```

Expected output:
```
retriever.py -- live AWS API smoke test

Endpoint: http://13.247.229.2:8000/api/documents/search/

  Query: How many days of annual leave do I get?
    [1.00] Determination and directive  (pdf)
    [0.95] Directive and determination  (pdf)
    [0.90] Determination  (pdf)
```

### Direct API Test (curl)
```bash
curl -X POST http://13.247.229.2:8000/api/documents/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "public service recruitment guidelines South Africa", "top_k": 5}'
```

## Document Corpus

### Coverage
- **Total Documents**: 2,605 DPSA PDFs/DOCs
- **Web Pages**: 133 scraped from www.dpsa.gov.za
- **Total Chunks**: ~35,000+ indexed text chunks
- **Update Frequency**: Managed by AWS/Scraping Team

### Document Types
- PDF policy documents
- Word documents (.doc, .docx)
- Web pages from DPSA website
- Circulars and directives
- Forms and applications
- Annual reports

## How It Works

### 1. Query Processing
When a user asks: *"How do I apply for leave?"*

1. Language detected (e.g., English)
2. Query sent to AWS endpoint:
   ```json
   {"query": "How do I apply for leave?", "top_k": 5}
   ```

### 2. Semantic Search (AWS Side)
- AWS converts query to embedding vector
- Performs cosine similarity search against 35,000+ document chunks
- Returns top-5 most relevant chunks with similarity scores

### 3. Result Processing (Our Side)
The retriever ([tools/retriever.py](../tools/retriever.py)) processes AWS results:
- Extracts document title, URL, content
- Assigns rank-based similarity scores (1.00 → 0.60)
- URL-encodes spaces in document paths
- Strips file extensions from titles for clean display

### 4. LLM Generation
Retrieved chunks are passed to the LLM ([tools/groq_client.py](../tools/groq_client.py)):
- Chunks provide context for answering the question
- LLM generates a grounded response
- Source links are attached for citation

## Schema Mapping

### AWS Response → Our Schema

| AWS Field | Our Schema Field | Notes |
|-----------|------------------|-------|
| `text` | `content` | The actual text chunk |
| `document_title` | `source_title` | Cleaned (file extensions removed) |
| `source_url` | `source_url` | URL-encoded for spaces |
| `id` | `id` | Unique chunk identifier |
| `similarity` | `similarity_score` | Rank-based 1.00–0.60 |
| (inferred) | `doc_type` | "pdf", "doc", or "webpage" |
| (static) | `category` | "DPSA Document" |

## Production Deployment

### For Cloudflare Pages / Vercel

Add environment variable:
```
AWS_SEARCH_URL=http://13.247.229.2:8000/api/documents/search/
```

### For Render (Backend)

Add to environment variables in Render dashboard:
```
AWS_SEARCH_URL=http://13.247.229.2:8000/api/documents/search/
MAX_RETRIEVAL_CHUNKS=5
RETRIEVER_TIMEOUT=10
```

## Troubleshooting

### Error: "Cannot reach AWS API"

**Possible causes:**
1. AWS server is down (check with AWS team)
2. Network/firewall blocking the connection
3. Incorrect endpoint URL

**Solution:**
```bash
# Test if endpoint is reachable
curl -I http://13.247.229.2:8000/api/documents/search/
```

### Error: "No results returned"

**Possible causes:**
1. Query is too vague or not related to DPSA content
2. top_k is set to 0
3. AWS database is empty

**Solution:**
- Test with a known query: "annual leave policy"
- Check AWS team's logs for the query
- Verify corpus has documents loaded

### Error: "HTTP 500 from AWS API"

**Possible causes:**
1. Malformed JSON in request
2. AWS backend error

**Solution:**
- Check your JSON formatting
- Contact AWS team with error details

### Timeout Errors

**Possible causes:**
1. Network latency
2. Large corpus search taking too long

**Solution:**
- Increase timeout in `.env`:
  ```
  RETRIEVER_TIMEOUT=30
  ```

## Performance Considerations

### Query Response Time
- **Average**: 500-2000ms per query
- **Factors**: Corpus size, network latency, AWS server load

### Optimization Tips
1. Keep queries concise and specific
2. Use appropriate `top_k` values (5 is optimal)
3. Cache results for identical queries (not yet implemented)

## Document Source Attribution

### URLs in Responses
All retrieved documents include source URLs for citation:
```
https://www.dpsa.gov.za/dpsa2g/documents/vacancies/2026/PSV%20CIRCULAR%2004%20of%202026.pdf
```

### URL Encoding
The retriever automatically encodes spaces in URLs:
- Input: `Annual Report 2025.pdf`
- Output: `Annual%20Report%202025.pdf`

This prevents broken links in the frontend.

## Integration Points

### Called By
- [demo/pipeline.py](../demo/pipeline.py) (Step 6: Retrieve relevant chunks)

### Calls
- AWS Semantic Search API (external HTTP endpoint)

### Dependencies
- Python `urllib` (HTTP client)
- Python `json` (payload/response parsing)
- `.env` configuration

## Known Limitations

### 1. English-Only Search
- AWS endpoint expects English queries
- Translation handled before retrieval (see [tools/translator.py](../tools/translator.py))

### 2. No Fuzzy Matching
- Exact semantic search only
- Typos may reduce result quality

### 3. Rank-Based Scores
- AWS returns ranked results (no raw similarity scores in some cases)
- We assign synthetic scores: 1.00, 0.95, 0.90, etc.

### 4. Fixed Corpus
- Documents managed by AWS team
- Cannot add/remove documents from chatbot side

## Future Enhancements

### Potential Improvements
- [ ] Response caching for identical queries
- [ ] Fallback to alternative search if AWS is down
- [ ] Query expansion (synonyms, acronyms)
- [ ] User feedback loop (thumbs up/down on results)
- [ ] Real-time corpus updates notification

## AWS Team Contact

For issues with the search endpoint or document corpus:
- **Team**: AWS/Scraping Team
- **Endpoint Health**: Check http://13.247.229.2:8000/health (if available)
- **Support**: Contact via project communication channels

## References

- **Retriever Implementation**: [tools/retriever.py](../tools/retriever.py)
- **Pipeline Integration**: [demo/pipeline.py](../demo/pipeline.py) (Step 6)
- **Workflow Documentation**: [workflows/query_handler.md](../workflows/query_handler.md)

---

**Last Updated**: 2026-04-09
**Maintained By**: AI Team
**AWS Endpoint Version**: v1 (2026-03)
