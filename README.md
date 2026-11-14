# CivicScope — Municipal Decision Explorer

CivicScope is a reusable, source-grounded prototype that helps residents understand municipal proposals: what may change, who could be affected, and how to participate.

Built for the 2026 CIVIC Hack. This is a hackathon prototype, **not** an official municipal service.

## What the MVP does

1. Upload a text-based municipal PDF (up to 10 MB / 300 pages). Longer documents are analyzed in parts and merged.
2. Extract the document's text using PyMuPDF.
3. Analyze it through a strict Pydantic output schema (local Ollama by default; optional OpenAI API).
4. Display a plain-language summary, potential impacts, participation details, and supporting PDF page references.
5. Identify missing or unverified information rather than inventing it.

**Important:** AI-generated claims are not official facts. The first version uses page-level excerpts as evidence. Team members must manually verify critical claims and external dates/URLs against the official municipal source before presenting or publishing results.

## Tech stack

- Frontend: React, TypeScript, Vite
- Backend: Python, FastAPI, PyMuPDF
- AI: Ollama local model (default) or optional OpenAI API (server-side only)
- Storage: no database in MVP; PDF contents are processed in memory

## Quick start

Requires Node.js 20.19+ (or 22.12+) and Python 3.11+.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Start Ollama and run: ollama pull qwen3:4b (no API key required).
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs ; health check: http://localhost:8000/health

If the configured Ollama service/model is missing, /analyze returns a clear configuration error, **not fabricated output**.

### Frontend

Open another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Visit http://localhost:5173 . Vite proxies /api to the backend at localhost:8000.

## How to test

1. Start both servers.
2. Upload a real, text-based municipal PDF.
3. Review the source page number for each extracted claim.
4. If Ollama is not running, verify the UI shows an actionable configuration error.
5. Test at least 3 different proposal types (e.g. roads, zoning, public facilities) and record actual vs expected outputs.

## Repo layout

```
frontend/              React UI
backend/app/           API, PDF parsing, AI extraction
backend/tests/         Backend tests
docs/                  Architecture, test plan, project requirements
data/sample_decisions/ Dataset documentation; do not commit unlicensed PDFs
.github/               Collaboration templates and CI
```

## Team workflow

Create branches from main (feature/frontend, feature/ai-analysis, feature/backend, docs/validation), make small pull requests, and have at least one teammate review important changes. Do not commit API keys, .env files or sensitive documents.

## Responsible AI and limitations

- Results are generated from supplied documents, not verified municipal records.
- The model may overlook context or misread complex tables; manually review outputs.
- Missing participation dates, impacts, or source excerpts must stay explicitly unconfirmed.
- Only show references to pages actually included in the uploaded PDF.
- This MVP handles selectable-text PDFs; scanned PDFs require separate OCR in a later version.
- Do not upload confidential documents to external AI services.

## License

No software license has been selected yet. Agree on a license with the team before adding one.

## Demo readiness

See [the audit and 36-hour plan](docs/hackathon-plan.md) for priorities, roles, demo script and remaining live validation. Text above 100,000 extracted characters is rejected rather than silently truncated. Quote matching checks source presence, not correctness of interpretation.

For a local demo use both servers above. Production hosting must forward `/api/*` to FastAPI with the `/api` prefix removed; Vite’s development proxy is not part of a static build.


## Free local AI and switching computers

The backend defaults to `AI_PROVIDER=ollama`. Install Ollama on the model
computer and run `ollama pull qwen3:4b`; copy `backend/.env.example` to
`backend/.env`. No API key is needed for local analysis. Set
`AI_PROVIDER=openai` and a valid `OPENAI_API_KEY` only if an authorized
paid provider is intentionally chosen.

The frontend can be on a different laptop than the model computer. See
[the portable two-computer setup](docs/multi-device-setup.md).
A document longer than one model request (20,000 characters locally) is split
by page into parts, each part is analyzed, and the checked statements are merged.
At most 12 parts are accepted, about 80-100 pages for a local model; a whole
council packet still needs the relevant section extracted first.
