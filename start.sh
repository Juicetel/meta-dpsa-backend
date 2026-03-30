#!/usr/bin/env bash
# start.sh — Start both the Python API and Nuxt frontend in one command
# Usage: bash start.sh

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "=== Batho Pele AI — Local Dev Startup ==="
echo ""

# ── 1. Check .env files ───────────────────────────────────────────────────────
if [ ! -f "$ROOT/.env" ]; then
  echo "[ERROR] Backend .env not found. Copy .env.example and fill in your keys:"
  echo "  cp .env.example .env"
  exit 1
fi

if [ ! -f "$ROOT/frontend/.env" ]; then
  echo "[ERROR] Frontend .env not found. Copy frontend/.env.example and fill in your keys:"
  echo "  cp frontend/.env.example frontend/.env"
  exit 1
fi

# ── 2. Activate Python virtualenv ────────────────────────────────────────────
if [ -f "$ROOT/venv/Scripts/activate" ]; then
  source "$ROOT/venv/Scripts/activate"   # Windows Git Bash
elif [ -f "$ROOT/venv/bin/activate" ]; then
  source "$ROOT/venv/bin/activate"       # Mac / Linux
else
  echo "[WARNING] No venv found. Using system Python."
  echo "  Create one with: python -m venv venv && pip install -r requirements.txt"
fi

# ── 3. Start Python API in background ────────────────────────────────────────
echo "[1/2] Starting Python API on http://localhost:8000 ..."
cd "$ROOT"
uvicorn api.main:app --reload --port 8000 &
API_PID=$!
echo "      PID: $API_PID"

# Wait for API to be ready
sleep 3
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
  echo "      Ready."
else
  echo "[WARNING] API may still be starting up. Check the logs above."
fi

# ── 4. Start Nuxt frontend ────────────────────────────────────────────────────
echo ""
echo "[2/2] Starting Nuxt frontend on http://localhost:3000 ..."
cd "$ROOT/frontend"
pnpm dev &
NUXT_PID=$!
echo "      PID: $NUXT_PID"

echo ""
echo "=== All services running ==="
echo "  Python API:  http://localhost:8000"
echo "  Nuxt App:    http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both."
echo ""

# Keep script running; kill both on Ctrl+C
trap "echo ''; echo 'Stopping...'; kill $API_PID $NUXT_PID 2>/dev/null; exit 0" INT
wait
