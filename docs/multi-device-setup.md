# Run CivicScope on another computer

The frontend, FastAPI backend, and local Ollama model are separate components.
No part of the UI hardcodes the model computer.

## Option A — Move everything to the stronger computer (recommended)

On the new Mac or Windows computer:

1. Clone the repository, install Node.js and Python 3.11+, and install [Ollama](https://ollama.com/download).
2. Run `ollama pull qwen3:4b`. On a lower-memory computer, use a smaller supported model and update `OLLAMA_MODEL`.
3. In `backend/`, create a Python virtual environment, install `requirements.txt`, and copy `.env.example` to `.env`.
4. Keep `AI_PROVIDER=ollama` and `OLLAMA_BASE_URL=http://127.0.0.1:11434`.
5. Run `uvicorn app.main:app --reload` from `backend/`.
6. In a second terminal, run `npm ci` and `npm run dev` from `frontend/`.
7. Open `http://localhost:5173`. Verify `http://localhost:8000/health`.

### Example commands for macOS

```bash
git clone https://github.com/juliazhang1015/civicscope-2026.git
cd civicscope-2026
ollama pull qwen3:4b
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open a separate terminal:

```bash
cd civicscope-2026/frontend
npm ci
npm run dev
```

Windows: run `py -3 -m venv .venv`, activate with
`.venv\\Scripts\\Activate.ps1`, and use `Copy-Item .env.example .env`.
If switching to a brand-new computer, clone the branch containing these changes
(or merge its PR first).

## Option B — Frontend on computer A, backend + Ollama on computer B

This is useful if computer B has more RAM or faster hardware.

1. Install Ollama, model, Python and the backend on computer B.
2. On B, keep `OLLAMA_BASE_URL=http://127.0.0.1:11434`.
3. On B, start FastAPI **only for your trusted private LAN**:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. Find B's local IPv4 address, such as `192.168.1.42`.
5. On A, start Vite with a proxy pointing at B:

   ```bash
   cd frontend
   API_PROXY_TARGET=http://192.168.1.42:8000 npm run dev
   ```

   In Windows PowerShell: set `$env:API_PROXY_TARGET="http://192.168.1.42:8000"`
   before running `npm run dev`.

6. Open the frontend on A at `http://localhost:5173`. Vite forwards `/api` to B.

`192.168.1.42` is **only an example**. Replace it with B's actual local IP.

**Security:** The demo FastAPI endpoint does not authenticate uploads.
Only run it on a private, trusted LAN, use your firewall, and stop it after the demo.
Do not expose port 8000 to the public internet. Ollama itself stays bound to
`127.0.0.1:11434` on B and does not need to be exposed remotely.

## Configuration

| Variable | Where | Purpose |
| --- | --- | --- |
| `AI_PROVIDER` | `backend/.env` | `ollama` (default) or `anthropic` |
| `OLLAMA_MODEL` | `backend/.env` | Local model name, default `qwen3:4b` |
| `OLLAMA_BASE_URL` | `backend/.env` | Ollama address **as seen by FastAPI** |
| `OLLAMA_NUM_CTX` | `backend/.env` | Model context budget |
| `OLLAMA_MAX_TEXT_CHARS` | `backend/.env` | Limit input rather than silently omit text |
| `OLLAMA_TIMEOUT_SECONDS` | `backend/.env` | Wait time for local model |
| `API_PROXY_TARGET` | frontend shell environment | FastAPI address **as seen by Vite** |

## Limitations

- The PDF parser accepts at most **300 pages / 10 MB**, regardless of model host.
- Local AI defaults to **20,000 extracted characters** per request, to protect
  smaller laptops. A longer document is split by page into parts (at most
  `ANALYSIS_MAX_PARTS`, default 12), analyzed one part at a time, and merged.
  Expect about a minute per part on a laptop.
- Model-generated citations must still match literal excerpts of uploaded PDF pages.
  This protects against invented quotes but cannot guarantee accurate interpretations.
- An independent publicly hosted site needs an authenticated backend and dedicated
  model hosting; this setup is for a **local hackathon demo**.
