"""
api/main.py
FastAPI HTTP wrapper around the DPSA Bot pipeline.

Exposes the pipeline as a REST API consumed by the Nuxt frontend.

Endpoints:
  GET  /health          → liveness check
  POST /session/new     → generate a fresh session ID
  POST /chat            → run the full 12-step pipeline and return a response

Run with:
  uvicorn api.main:app --reload --port 8000
"""

import sys
import uuid
from pathlib import Path

# Ensure project root is on the path so tool imports work
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from demo.pipeline import run_pipeline

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Batho Pele AI API",
    description="REST API for the DPSA multilingual chatbot pipeline",
    version="1.0.0",
)

# Allow the Nuxt dev server and any deployed frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ImageAttachment(BaseModel):
    base64: str
    media_type: str

class ChatRequest(BaseModel):
    query: str
    session_id: str
    images: list[ImageAttachment] = []

class NewSessionResponse(BaseModel):
    session_id: str

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Liveness check — returns 200 when the API is up."""
    return {"status": "ok", "service": "Batho Pele AI"}


@app.post("/session/new", response_model=NewSessionResponse)
def new_session():
    """Generate a new session ID for a fresh conversation."""
    return NewSessionResponse(session_id=str(uuid.uuid4())[:8])


@app.post("/chat")
def chat(req: ChatRequest):
    """
    Run the full 12-step pipeline for a user query.

    Returns:
        response      (str)   — final response in the user's language
        source_links  (list)  — [{title, url}] documents used
        followups     (list)  — suggested follow-up questions
        language      (str)   — ISO language code detected
        confidence    (float) — response confidence 0.0–1.0
        steps         (list)  — pipeline step trace [{step, name, detail}]
    """
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    images = [{"base64": img.base64, "media_type": img.media_type} for img in req.images]
    result = run_pipeline(query, req.session_id, images=images)
    return result
