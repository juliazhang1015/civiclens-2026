# CivicScope backend integration notes

## Scope
This change only updates `backend/app/main.py` and adds HTTP-boundary tests. It does not modify Julia's frontend, AI analyzer, quote verification, schemas, PDF reader, dependency file, or CI workflow.

## Run locally
From the repo root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
# Configure OPENAI_API_KEY in backend/.env on your own computer only.
python -m pytest -q
uvicorn app.main:app --reload --port 8000
```

Start the frontend in a separate terminal from `frontend/` with `npm ci && npm run dev`. The development proxy maps `/api/analyze` to FastAPI's `/analyze`; direct API docs are at `http://localhost:8000/docs`.

## Test without exposing an API key
`python -m pytest -q` uses monkeypatched analyzer responses for HTTP-boundary tests. The tests do not make provider calls. They are **not** evidence that a live model succeeds.

## Demo acceptance
1. Use a text-selectable official PDF **within 10 MB and 25 pages** and under the analyzer's extracted-text limit.
2. Start backend and frontend. Open `http://localhost:5173`.
3. Upload a valid municipal PDF. Confirm that fields, source quotations, PDF page links and unknowns render.
4. Upload non-PDF / empty / encrypted / scanned PDF and confirm an actionable error.
5. Confirm actual AI output manually against the PDF. Evidence quote matching only proves the quote is present on the page, not that its interpretation is correct.

## Deployment
Vite's proxy only runs during local development. For a production static frontend, use a reverse proxy to map `/api/*` to FastAPI `/*` with the prefix removed. Alternatively point frontend requests at an explicit backend URL and configure a strict FastAPI CORS allowlist for the actual frontend origin. Do not use wildcard CORS with credentials. Keep `OPENAI_API_KEY` in backend server environment variables (or an ignored local `.env`), not the frontend bundle.

## Remaining limitations
No live-provider integration was tested by this patch. Real PDFs need manual content review. An in-progress provider request may continue after a user cancels the browser request. Upload and text limits remain unchanged.
