# Batho Pele AI — DPSA Chatbot

A multilingual AI chatbot for the Department of Public Service and Administration (DPSA), built on the WAT framework (Workflows · Agents · Tools).

- **Python FastAPI** backend with a 12-step pipeline (Groq Llama 3.3 70B + vision)
- **Nuxt 4** frontend with NuxtHub (SQLite, blob storage, GitHub auth)
- Supports all 11 South African official languages via Google Cloud Translation

---

## Repo Structure

```
meta-dpsa-backend/
├── api/              ← FastAPI server (entry point: api/main.py)
├── tools/            ← Groq client, translator, lang detector, retriever
├── demo/             ← 12-step pipeline orchestrator (demo/pipeline.py)
├── workflows/        ← Markdown SOPs for each pipeline stage
├── requirements.txt  ← Python dependencies
├── render.yaml       ← One-click Render deployment config
├── .env.example      ← Backend env var template
└── frontend/         ← Nuxt 4 chatbot UI
    ├── app/          ← Pages, components, composables
    ├── server/       ← Nuxt server routes + DB schema
    ├── nuxt.config.ts
    └── .env.example  ← Frontend env var template
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | https://python.org |
| Node.js | 20+ | https://nodejs.org |
| pnpm | 9+ | `npm i -g pnpm` |

---

## Local Development

### 1. Clone the repo

```bash
git clone https://github.com/Juicetel/meta-dpsa-backend.git
cd meta-dpsa-backend
```

### 2. Set up the Python backend

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
# source venv/bin/activate      # Mac / Linux

# Install dependencies
pip install -r requirements.txt

# Copy env template and fill in your keys
cp .env.example .env
```

Edit `.env` and add your keys (see [Environment Variables](#environment-variables) below).

```bash
# Start the API (runs on http://localhost:8000)
uvicorn api.main:app --reload --port 8000
```

Verify it's running: http://localhost:8000/health → `{"status":"ok"}`

### 3. Set up the Nuxt frontend

```bash
cd frontend

# Install dependencies
pnpm install

# Copy env template and fill in your keys
cp .env.example .env
```

Edit `frontend/.env` and add your keys.

```bash
# Start the dev server (runs on http://localhost:3000)
pnpm dev
```

### 4. Start both with one command

From the repo root (requires two terminals or use the script below):

**Terminal 1 — Python API:**
```bash
source venv/Scripts/activate && uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — Nuxt frontend:**
```bash
cd frontend && pnpm dev
```

Or use the provided script:
```bash
bash start.sh
```

---

## Environment Variables

### Backend (`/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key — https://console.groq.com |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes (local) | Path to Google service account JSON file |
| `GOOGLE_CREDENTIALS_JSON` | Yes (cloud) | Full JSON content of the service account (for Render) |
| `AWS_SEARCH_URL` | Yes | Document search endpoint from the AWS team |
| `GROQ_MODEL` | No | Default: `llama-3.3-70b-versatile` |
| `GROQ_VISION_MODEL` | No | Default: `meta-llama/llama-4-scout-17b-16e-instruct` |
| `MAX_RETRIEVAL_CHUNKS` | No | Default: `5` |
| `RETRIEVER_TIMEOUT` | No | Default: `10` (seconds) |

### Frontend (`/frontend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NUXT_SESSION_PASSWORD` | Yes | Random string, min 32 chars — used for session encryption |
| `NUXT_DPSA_API_URL` | Yes | URL of the Python API (e.g. `http://localhost:8000` locally, or your Render URL) |
| `NUXT_OAUTH_GITHUB_CLIENT_ID` | Optional | GitHub OAuth app client ID (for login) |
| `NUXT_OAUTH_GITHUB_CLIENT_SECRET` | Optional | GitHub OAuth app secret (for login) |

> **Tip:** Generate a session password with: `python -c "import secrets; print(secrets.token_hex(32))"`

---

## Deploying a Staging Link

### Option A: Render (Python API) + NuxtHub (Frontend) — Recommended

#### Step 1: Deploy the Python API to Render

1. Go to https://dashboard.render.com → **New Web Service**
2. Connect your GitHub repo: `Juicetel/meta-dpsa-backend`
3. Render will auto-detect `render.yaml` — click **Apply**
4. In the **Environment** tab, add these secrets:
   - `GROQ_API_KEY` → your Groq API key
   - `GOOGLE_CREDENTIALS_JSON` → paste the full content of your `google-credentials.json` file
5. Click **Deploy** — your API URL will be something like `https://dpsa-bot-api.onrender.com`

#### Step 2: Deploy the Frontend to NuxtHub

1. Go to https://hub.nuxt.com → **New Project**
2. Connect GitHub repo: `Juicetel/meta-dpsa-backend`
3. Set **Root Directory** to `frontend`
4. Add environment variables:
   - `NUXT_SESSION_PASSWORD` → random 32-char string
   - `NUXT_DPSA_API_URL` → your Render API URL from Step 1
   - `NUXT_OAUTH_GITHUB_CLIENT_ID` / `NUXT_OAUTH_GITHUB_CLIENT_SECRET` → optional (for login)
5. Deploy — NuxtHub gives you a `*.nuxt.dev` URL

#### Step 3: Allow the NuxtHub URL in the Python API

Once you have the NuxtHub URL (e.g. `https://dpsa-chatbot.nuxt.dev`), update the CORS list in [api/main.py](api/main.py#L43):

```python
allow_origins=[
    "http://localhost:3000",
    "https://dpsa-chatbot.nuxt.dev",   # ← add your NuxtHub URL here
],
```

Commit and push — Render will auto-redeploy.

---

## API Reference

Base URL (local): `http://localhost:8000`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `POST` | `/session/new` | Create a new session ID |
| `POST` | `/chat` | Run the 12-step pipeline |

**POST /chat — Request body:**
```json
{
  "query": "How do I apply for early retirement?",
  "session_id": "abc12345",
  "images": []
}
```

**POST /chat — Response:**
```json
{
  "response": "To apply for early retirement...",
  "source_links": [{"title": "Early Retirement Policy", "url": "..."}],
  "followups": ["What are the eligibility criteria?"],
  "language": "en",
  "confidence": 0.85
}
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI inference | Groq (Llama 3.3 70B text, Llama 4 Scout vision) |
| Translation | Google Cloud Translation API |
| Document search | AWS OpenSearch (via REST API) |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Frontend | Nuxt 4, Vue 3, Vercel AI SDK v6 |
| Storage | NuxtHub (SQLite via hub:db, files via hub:blob) |
| Auth | GitHub OAuth (nuxt-auth-utils) |
| Deployment | Render (API) + NuxtHub (frontend) |
