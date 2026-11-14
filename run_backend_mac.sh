#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
if [[ ! -f backend/requirements.txt || ! -f backend/app/main.py ]]; then
  echo 'ERROR: Put this script at the repository root alongside backend/.' >&2
  exit 1
fi
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
cd backend
if [[ -f .env ]]; then
  echo 'backend/.env exists. Keep it out of Git.'
else
  echo 'No backend/.env found. Real AI analysis may require OPENAI_API_KEY there.'
fi
exec python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
