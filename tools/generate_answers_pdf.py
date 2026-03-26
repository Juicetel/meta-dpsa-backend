"""
Generate a formatted PDF of the homework answers for questions 2, 3, 5, 11, and 12.
Output: homework_answers.pdf in the project root.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY

OUTPUT_PATH = "homework_answers.pdf"

# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------

QUESTIONS = [
    {
        "number": "Question 2",
        "title": "Full Technical Architecture & Llama Integration",
        "body": [
            {
                "type": "para",
                "text": (
                    "The platform is built on the <b>WAT framework</b> (Workflows, Agents, Tools) — "
                    "a three-layer architecture that separates probabilistic AI reasoning from "
                    "deterministic execution:"
                ),
            },
            {
                "type": "bullets",
                "items": [
                    "<b>Layer 1 — Workflows:</b> Markdown SOPs (stored in <i>workflows/</i>) define "
                    "objectives, required inputs, tool sequences, and edge-case handling. Core "
                    "workflows include query_handler.md, document_ingest.md, language_router.md, "
                    "and escalation.md.",
                    "<b>Layer 2 — Agent (AI Orchestrator):</b> Reads the relevant workflow, decides "
                    "which tools to invoke, handles failures, routes escalations, and maintains "
                    "session coherence. It does not perform deterministic tasks itself — those are "
                    "delegated.",
                    "<b>Layer 3 — Tools:</b> Python scripts in <i>tools/</i> that execute every "
                    "concrete operation: language detection, translation, vector retrieval, LLM "
                    "calls, session management, logging, and follow-up generation.",
                ],
            },
            {
                "type": "para",
                "text": (
                    "The <b>12-step query pipeline</b> (pipeline.py) processes every user query through: "
                    "(1) emoji parsing for semantic enrichment, (2) image/sticker processing via "
                    "Llama Vision — Phase 2, (3) language detection via Google Cloud Translate, "
                    "(4) translation to English if needed, (5) session context loading, "
                    "(6) chunk retrieval from the knowledge base, (7) LLM response generation, "
                    "(8) confidence/grounding check at threshold 0.6, (9) back-translation to the "
                    "user's language, (10) follow-up suggestion generation, (11) session save, and "
                    "(12) POPIA-compliant audit logging."
                ),
            },
            {
                "type": "para",
                "text": (
                    "<b>Llama Integration:</b> The production specification calls for Meta's "
                    "<b>Llama 3.2-Vision</b> deployed on an AWS EC2 instance owned by the "
                    "infrastructure team. The AI team's llm_client.py passes structured prompts "
                    "(system prompt + retrieved chunks + user query) to the Llama inference "
                    "endpoint via HTTP. During the current demo phase, the Claude API serves as a "
                    "drop-in stand-in while the Llama endpoint is being provisioned. Llama "
                    "3.2-Vision was selected specifically for Phase 2 multimodal capability — "
                    "enabling the bot to interpret images, forms, and diagrams submitted by users "
                    "(e.g., photos of government forms or ID documents)."
                ),
            },
        ],
    },
    {
        "number": "Question 3",
        "title": "RAG Architecture & Grounding in Verified Public-Sector Data",
        "body": [
            {
                "type": "para",
                "text": (
                    "<b>Yes, RAG is implemented architecturally</b>, with production deployment "
                    "pending final infrastructure integration."
                ),
            },
            {
                "type": "subheading",
                "text": "The production RAG pipeline:",
            },
            {
                "type": "numbered",
                "items": [
                    "The AWS/Scraping team crawls DPSA and other public-sector portals, extracts "
                    "and chunks text, generates vector embeddings, and stores everything in a "
                    "<b>Postgres database with the pgvector extension</b>.",
                    "On every query, retriever.py embeds the user's query and performs a "
                    "<b>cosine similarity search</b> against the vector store, returning the "
                    "top-k most relevant document chunks.",
                    "Those chunks — along with their source URLs and titles — are injected into "
                    "the LLM's context window.",
                    "The system prompt enforces a <b>hard grounding rule</b>: \"Answer ONLY from "
                    "the retrieved chunks. Never use training knowledge.\" If no relevant chunks "
                    "are found, the system escalates to a human agent rather than hallucinating.",
                    "A <b>confidence threshold</b> (≥ 0.6, based on how many retrieved chunks "
                    "were cited in the response) gates every output — low-confidence responses "
                    "trigger escalation, not delivery.",
                ],
            },
            {
                "type": "para",
                "text": (
                    "<b>Verified data sources:</b> DPSA policies, HR procedures, leave "
                    "regulations, ministerial circulars, legislative records, and approved "
                    "government portals — all ingested, chunked, and stored by the scraping team, "
                    "with a timestamped scraped_at field for freshness tracking."
                ),
            },
            {
                "type": "para",
                "text": (
                    "<b>Current demo state:</b> While pgvector credentials are pending from the "
                    "infrastructure team, the demo uses mock_retriever.py — a keyword-frequency "
                    "retriever against a static JSON knowledge base of 10 document chunks covering "
                    "DPSA's most queried topics (leave entitlements, Z83 forms, PMDS, grievances, "
                    "etc.). It includes 170+ synonym mappings and domain stop-word filtering to "
                    "simulate retrieval quality."
                ),
            },
            {
                "type": "para",
                "text": (
                    "<b>Document freshness</b> is handled by document_ingest.md + reindexer.py: "
                    "S3 event notifications trigger incremental re-indexing whenever the scraper "
                    "deposits new content, using scraped_at timestamps to fetch only new or "
                    "updated chunks."
                ),
            },
        ],
    },
    {
        "number": "Question 5",
        "title": "Guardrails & Safety Systems",
        "body": [
            {
                "type": "para",
                "text": (
                    "The platform implements a layered safety architecture spanning prompt-level "
                    "rules, retrieval-time validation, response-time confidence gating, escalation "
                    "logic, privacy enforcement, and session controls. The full set of guardrails "
                    "is described below."
                ),
            },
            {
                "type": "subheading",
                "text": "1. Content Grounding (Non-Negotiable Hard Rule)",
            },
            {
                "type": "para",
                "text": (
                    "The system prompt (prompts/system_prompt.md) contains an explicitly labelled "
                    "<b>NON-NEGOTIABLE GROUNDING RULE</b>: the model must answer exclusively from "
                    "retrieved document chunks and never draw on its training knowledge. Any claim "
                    "not supported by a retrieved chunk must be withheld. The model is instructed "
                    "to use attribution phrases such as \"According to [Document Title]...\" rather "
                    "than stating facts as absolute truth. It is explicitly prohibited from "
                    "inventing policies, procedures, contact numbers, or URLs."
                ),
            },
            {
                "type": "subheading",
                "text": "2. Confidence Scoring & Response Gating",
            },
            {
                "type": "para",
                "text": (
                    "Every response produced by llm_client.py is assigned a <b>confidence score "
                    "(0.0–1.0)</b> based on the ratio of retrieved chunks actually cited in the "
                    "response. A response that cites no chunks scores 0.3 (suspicious); a response "
                    "with zero retrieved chunks scores 0.0. The query pipeline in pipeline.py "
                    "applies a configurable threshold (default <b>RESPONSE_CONFIDENCE_THRESHOLD = "
                    "0.6</b>) — any response below this threshold is <i>discarded</i> and the "
                    "query is escalated rather than returned to the user."
                ),
            },
            {
                "type": "subheading",
                "text": "3. Five-Trigger Escalation System",
            },
            {
                "type": "para",
                "text": (
                    "The escalation.md workflow defines five explicit conditions that route a query "
                    "away from automated response to a human agent or a transparent failure message:"
                ),
            },
            {
                "type": "numbered",
                "items": [
                    "<b>No chunks retrieved</b> — retriever.py returns zero results for the query.",
                    "<b>Low response confidence</b> — response confidence falls below the 0.6 threshold.",
                    "<b>Out-of-scope query</b> — query is unrelated to DPSA public services.",
                    "<b>Grounding failure</b> — response cannot be verified against retrieved chunks.",
                    "<b>Repeated clarification failure</b> — user asked to clarify twice without resolution.",
                ],
            },
            {
                "type": "para",
                "text": (
                    "Each trigger has a distinct, honest response template (e.g., \"I found some "
                    "related information, but I'm not confident it fully answers your question...\") "
                    "— the system never silently returns a low-quality answer."
                ),
            },
            {
                "type": "subheading",
                "text": "4. Scope Boundary Enforcement",
            },
            {
                "type": "para",
                "text": (
                    "The system prompt defines explicit out-of-scope categories with scripted "
                    "responses: personal legal advice, queries about other government departments, "
                    "complaints about officials (routed to the Public Service Commission), "
                    "salary/PERSAL queries (routed to departmental HR), and any topic outside "
                    "the DPSA knowledge base. Out-of-scope queries trigger escalation rather "
                    "than a hallucinated response."
                ),
            },
            {
                "type": "subheading",
                "text": "5. POPIA Compliance & Privacy Protection",
            },
            {
                "type": "para",
                "text": (
                    "Privacy-by-design is enforced at multiple layers in accordance with South "
                    "Africa's Protection of Personal Information Act (POPIA):"
                ),
            },
            {
                "type": "bullets",
                "items": [
                    "The system prompt explicitly forbids collecting ID numbers, salary details, "
                    "grievance case numbers, or any user-identifying information. If a user "
                    "volunteers PII, the model is instructed not to repeat it back or store it.",
                    "logger.py stores only metadata (timestamps, session UUID, language code, "
                    "query length, latency, confidence score) — raw query text is excluded from "
                    "logs by default and requires explicit POPIA officer approval to enable.",
                    "Session IDs are UUIDs, not employee identifiers. Session history stores "
                    "only role, message text, language, and timestamp.",
                    "Voice audio files (Phase 2) are auto-purged from .tmp/ after a configurable "
                    "TTL (default 300 seconds). No voice recordings are stored permanently.",
                ],
            },
            {
                "type": "subheading",
                "text": "6. Retrieval Limits & Hard Caps",
            },
            {
                "type": "bullets",
                "items": [
                    "<b>MAX_RETRIEVAL_CHUNKS</b> (default 5) — bounds the number of document "
                    "chunks injected into the LLM context, preventing context flooding.",
                    "<b>max_tokens = 1024</b> — hard cap on response length in llm_client.py.",
                    "<b>MAX_CONTEXT_TURNS = 10</b> — session_store.py automatically truncates "
                    "conversation history beyond 10 turns (20 messages) to prevent unbounded "
                    "context growth.",
                    "<b>SESSION_TTL_SECONDS = 3600</b> — sessions auto-expire after one hour "
                    "of inactivity.",
                ],
            },
            {
                "type": "subheading",
                "text": "7. Language Detection Confidence & Unsupported Language Handling",
            },
            {
                "type": "para",
                "text": (
                    "lang_detector.py returns a confidence score alongside every detected language. "
                    "language_router.md applies three routing rules: high confidence (≥ 0.8) "
                    "proceeds normally; medium confidence (0.5–0.8) is flagged as uncertain; "
                    "low confidence (&lt; 0.5) defaults to English. Tshivenda and isiNdebele — "
                    "the two SA official languages not supported by any mainstream translation "
                    "provider — are explicitly detected and handled with a graceful English "
                    "fallback and a user-facing apology message."
                ),
            },
            {
                "type": "subheading",
                "text": "8. Input Validation & Malformed Data Handling",
            },
            {
                "type": "bullets",
                "items": [
                    "llm_client.py raises ValueError on empty queries before any API call is made.",
                    "mock_retriever.py raises ValueError on None queries and returns an empty list "
                    "(triggering escalation) when no keyword matches are found.",
                    "reindexer.py validates every chunk on ingest — chunks missing content or a "
                    "source URL are skipped and logged, not silently ingested.",
                    "emoji_parser.py filters out unrecognised emoji mappings to avoid injecting "
                    "noise into the query.",
                ],
            },
            {
                "type": "subheading",
                "text": "9. Source Attribution & Audit Trail",
            },
            {
                "type": "para",
                "text": (
                    "Every response includes source citations (document title + URL) drawn from "
                    "the retrieved chunks used. llm_client.py tracks which chunk IDs were cited "
                    "(used_chunk_ids) and pipeline.py surfaces deduplicated source links in the "
                    "UI. This creates an auditable chain from user query → retrieved evidence → "
                    "generated response. All interactions, escalations, reindex events, and "
                    "errors are written to structured NDJSON audit logs in .tmp/logs/."
                ),
            },
            {
                "type": "subheading",
                "text": "10. Voice Input Confidence Gate (Phase 2)",
            },
            {
                "type": "para",
                "text": (
                    "For the planned voice channel, voice_handler.md defines a "
                    "<b>STT_CONFIDENCE_THRESHOLD</b> (default 0.75). Speech-to-text transcripts "
                    "scoring below this threshold are not processed — the user is prompted to "
                    "repeat or switch to text input. Low-confidence transcripts are never "
                    "silently passed to the LLM pipeline."
                ),
            },
            {
                "type": "subheading",
                "text": "Note on Llama Guard",
            },
            {
                "type": "para",
                "text": (
                    "Meta's Llama Guard (a dedicated content moderation classifier) has not yet "
                    "been integrated into the pipeline. The current safety posture relies on "
                    "the system prompt's hard scope rules, the confidence gate, the escalation "
                    "system, and retrieval-grounded generation. Llama Guard integration is a "
                    "candidate for the production hardening phase once the Llama inference "
                    "endpoint is live, and would provide an additional moderation layer before "
                    "responses are returned to users."
                ),
            },
        ],
    },
    {
        "number": "Question 11",
        "title": "Simulations, Stakeholder Demos & Early Insights",
        "body": [
            {
                "type": "para",
                "text": "<b>Yes — a full end-to-end proof-of-concept demo has been completed.</b>",
            },
            {
                "type": "para",
                "text": (
                    "The demo is a functional Streamlit web application running the complete "
                    "Phase 1 pipeline (all 12 steps), featuring a chat-bubble UI with message "
                    "history, real-time step-by-step pipeline visibility in the sidebar, source "
                    "citation display with every response, follow-up suggestion buttons for "
                    "natural conversation flow, and live language detection and translation across "
                    "9 of South Africa's 11 official languages."
                ),
            },
            {
                "type": "subheading",
                "text": "Early insights from the demo phase:",
            },
            {
                "type": "bullets",
                "items": [
                    "<b>Language routing works reliably.</b> Google Translate handles 9/11 "
                    "official languages with acceptable quality. Tshivenda and isiNdebele are "
                    "not supported by any mainstream provider; fallback to English was "
                    "implemented, flagging Lelapa AI (SA-based NLP provider) for future "
                    "evaluation.",
                    "<b>Emoji enrichment adds real value.</b> Many users, particularly on "
                    "mobile, communicate intent through emojis. The emoji parser maps common "
                    "symbols to semantic context (e.g., 🏥 → health/sick leave queries), "
                    "materially improving retrieval relevance for informal inputs.",
                    "<b>The escalation pathway is essential.</b> When the mock retriever "
                    "returned zero results or low-confidence responses, user experience degraded "
                    "sharply without escalation. The 0.6 confidence threshold and clean "
                    "escalation to human agents proved to be a critical design decision.",
                    "<b>Follow-up suggestions drive engagement.</b> Template-based follow-up "
                    "buttons (generated from 4 category banks: benefits, procedures, policies, "
                    "employment) noticeably extended conversation depth in testing, surfacing "
                    "information users did not know to ask for.",
                    "<b>The WAT framework separation of concerns proved reliable.</b> Isolating "
                    "AI orchestration from deterministic tool execution made the demo highly "
                    "debuggable; failures were always traceable to a specific tool step rather "
                    "than opaque LLM behaviour.",
                    "<b>Session coherence matters for multi-turn queries.</b> Users frequently "
                    "ask follow-up questions that reference earlier turns (e.g., \"How do I "
                    "apply for that?\" after a leave entitlement answer). In-memory session "
                    "history with the last N turns injected into context handled this well at "
                    "demo scale.",
                ],
            },
        ],
    },
    {
        "number": "Question 12",
        "title": "Most Significant Technical Challenges with Llama Deployment",
        "body": [
            {
                "type": "bullets",
                "items": [
                    "<b>1. Cross-team integration dependency (most critical).</b> The Llama "
                    "3.2-Vision model is hosted on an AWS EC2 instance owned by a separate "
                    "infrastructure team. The AI team's llm_client.py is designed to call an "
                    "external Llama inference endpoint, but LLAMA_API_ENDPOINT and "
                    "LLAMA_API_KEY remain empty pending that team's delivery. This means the "
                    "entire LLM layer in production is currently untested. The demo works only "
                    "because the Claude API serves as a drop-in stand-in.",
                    "<b>2. Embedding model alignment.</b> RAG correctness depends on the query "
                    "embedding at retrieval time matching the document embeddings stored in "
                    "pgvector at ingestion time. The infrastructure team generates embeddings "
                    "during scraping; the AI team must use the identical model when embedding "
                    "queries. The model name and vector dimensions (assumed 1536, but "
                    "unconfirmed) remain a critical open item. A mismatch would silently degrade "
                    "retrieval quality without obvious errors.",
                    "<b>3. No direct access to the knowledge base during development.</b> The "
                    "AI team has no pgvector credentials, which means retriever.py — the core "
                    "of the RAG system — is a documented stub. Integration testing of the full "
                    "pipeline (query → embedding → cosine similarity → chunk retrieval → LLM "
                    "response) cannot happen until the infrastructure team delivers database "
                    "access.",
                    "<b>4. Confidence scoring is heuristic-based.</b> Because the Llama "
                    "endpoint is not yet accessible, the confidence scoring logic in "
                    "llm_client.py uses a simple citation-count heuristic. This cannot be "
                    "calibrated against actual Llama outputs until the endpoint is live, "
                    "creating risk that the 0.6 threshold is incorrectly tuned for the "
                    "production model's behaviour.",
                    "<b>5. Multimodal (Vision) capability deferred to Phase 2.</b> Llama "
                    "3.2-Vision was selected partly for its ability to process images submitted "
                    "by users — a key use case for citizens photographing forms or documents. "
                    "However, the image-processing step is currently skipped in Phase 1, and "
                    "all voice input/output (stt_transcriber.py, tts_synthesizer.py) is marked "
                    "\"Phase 2 — Do Not Implement Yet\". This defers a major capability of the "
                    "chosen model.",
                ],
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Build PDF
# ---------------------------------------------------------------------------

def build_pdf(output_path: str) -> None:
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    base_styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=base_styles["Title"],
        fontSize=18,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=6,
        fontName="Helvetica-Bold",
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=base_styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#555555"),
        spaceAfter=20,
        fontName="Helvetica",
    )

    question_num_style = ParagraphStyle(
        "QuestionNum",
        parent=base_styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#ffffff"),
        fontName="Helvetica-Bold",
        leftIndent=0,
        leading=14,
    )

    question_title_style = ParagraphStyle(
        "QuestionTitle",
        parent=base_styles["Normal"],
        fontSize=13,
        textColor=colors.HexColor("#1a1a2e"),
        fontName="Helvetica-Bold",
        spaceBefore=18,
        spaceAfter=8,
        leftIndent=0,
        leading=18,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=base_styles["Normal"],
        fontSize=10.5,
        textColor=colors.HexColor("#222222"),
        fontName="Helvetica",
        leading=16,
        spaceAfter=8,
        alignment=TA_JUSTIFY,
    )

    bullet_style = ParagraphStyle(
        "Bullet",
        parent=body_style,
        leftIndent=14,
        bulletIndent=0,
        spaceAfter=5,
        alignment=TA_LEFT,
    )

    subheading_style = ParagraphStyle(
        "SubHeading",
        parent=base_styles["Normal"],
        fontSize=10.5,
        textColor=colors.HexColor("#1a1a2e"),
        fontName="Helvetica-Bold",
        spaceBefore=6,
        spaceAfter=4,
    )

    story = []

    # Document header
    story.append(Paragraph("Homework Answers", title_style))
    story.append(Paragraph("Questions 2, 3, 5, 11 &amp; 12 — Juicetel AI Platform", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 14))

    for q in QUESTIONS:
        # Question heading
        story.append(
            Paragraph(
                f"<font color='#2563eb'><b>{q['number']}</b></font> — {q['title']}",
                question_title_style,
            )
        )
        story.append(
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d1d5db"))
        )
        story.append(Spacer(1, 6))

        for block in q["body"]:
            if block["type"] == "para":
                story.append(Paragraph(block["text"], body_style))

            elif block["type"] == "subheading":
                story.append(Paragraph(block["text"], subheading_style))

            elif block["type"] == "bullets":
                items = []
                for item in block["items"]:
                    items.append(
                        ListItem(
                            Paragraph(item, bullet_style),
                            bulletColor=colors.HexColor("#2563eb"),
                            leftIndent=20,
                            bulletText="•",
                        )
                    )
                story.append(ListFlowable(items, bulletType="bullet", leftIndent=10))
                story.append(Spacer(1, 4))

            elif block["type"] == "numbered":
                items = []
                for i, item in enumerate(block["items"], 1):
                    items.append(
                        ListItem(
                            Paragraph(item, bullet_style),
                            bulletColor=colors.HexColor("#2563eb"),
                            leftIndent=20,
                            value=i,
                        )
                    )
                story.append(ListFlowable(items, bulletType="1", leftIndent=10))
                story.append(Spacer(1, 4))

        story.append(Spacer(1, 10))

    doc.build(story)
    print(f"PDF generated: {output_path}")


if __name__ == "__main__":
    build_pdf(OUTPUT_PATH)
