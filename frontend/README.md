# Batho Pele AI — Frontend

Official Nuxt 3 frontend for the **DPSA Batho Pele AI** chatbot — a multilingual public-sector assistant for South African government employees.

Built on [Nuxt UI](https://ui.nuxt.com) and the [Vercel AI SDK](https://ai-sdk.dev), connected to the [DPSA Bot Python pipeline](https://github.com/Juicetel/meta-dpsa-backend) via a FastAPI backend.

---

## Architecture

```
Browser (Nuxt 3)
  └─► Nuxt Nitro server  (/api/chats/[id])
        └─► DPSA Python API  (FastAPI, port 8000)
              └─► 12-step RAG pipeline
                    ├─ Language detection & translation (9 SA languages)
                    ├─ Vector retrieval (pgvector / mock)
                    ├─ LLM generation (Llama 3.2 / Claude stand-in)
                    └─ Confidence gating & escalation
```

---

## Quick Start

### 1. Start the Python API (DPSA Bot repo)

```bash
cd "../DPSA Bot"
uvicorn api.main:app --reload --port 8000
```

### 2. Install and run the frontend

```bash
pnpm install
pnpm db:migrate
pnpm dev
```

Open **http://localhost:3000**

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
# Required — session encryption (min 32 chars)
NUXT_SESSION_PASSWORD=<random-32-char-string>

# Required — points to the running Python pipeline API
DPSA_API_URL=http://localhost:8000

# Optional — GitHub OAuth login
NUXT_OAUTH_GITHUB_CLIENT_ID=
NUXT_OAUTH_GITHUB_CLIENT_SECRET=

# Optional — file uploads (local filesystem used by default in dev)
BLOB_READ_WRITE_TOKEN=
```

> **Note:** `AI_GATEWAY_API_KEY` is no longer required. All AI responses are served by the Python DPSA pipeline.

---

## Features

- **Multilingual chat** — supports 9 of South Africa's 11 official languages
- **RAG-grounded responses** — every answer is sourced from verified DPSA documents
- **Source citations** — links to the original government documents used
- **Follow-up suggestions** — contextual next questions after each answer
- **Chat history** — persisted in SQLite (Turso in production)
- **File uploads** — attach documents, images, or PDFs to queries
- **GitHub authentication** — optional OAuth login
- **Dark / light mode** — full theme support

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend framework | Nuxt 3 |
| UI components | Nuxt UI 4 + Tailwind CSS 4 |
| Server runtime | Nitro (via Nuxt) |
| AI streaming | Vercel AI SDK |
| Database | SQLite (dev) / Turso (prod) via Drizzle ORM |
| File storage | NuxtHub Blob (local / Vercel / S3) |
| Authentication | nuxt-auth-utils (GitHub OAuth) |
| AI backend | DPSA Python pipeline (FastAPI + Llama 3.2) |

---

## Production Deploy

```bash
pnpm build
pnpm preview
```

Ensure `DPSA_API_URL` points to the deployed Python API instance in your production environment variables.
