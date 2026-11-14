# CivicScope PR #6 corrected integration pack

This package contains **additive tools only**, not a complete FastAPI backend. It assumes the repository already has `backend/app/main.py`, `backend/requirements.txt`, PDF reader and analyzer. It does not modify Julia's analyzer or frontend.

## Correct locations (relative to repository root)

- `run_backend_mac.sh`
- `backend/tests/smoke_api.py`
- `demo_samples/waterloo_lease_2pages.pdf`
- `README_UPLOAD.md` (optional documentation)

Copy these files into the **matching paths** in your checked-out `feature/Backend` branch. Do not upload the ZIP as a single file to GitHub. Remove old misplaced copies in `backend/app/` and any tracked `.pyc`.

## Run on Mac

From repository root:

```bash
chmod +x run_backend_mac.sh
./run_backend_mac.sh
```

The script installs backend dependencies and runs `uvicorn` at `http://127.0.0.1:8000`. In a second terminal, from repository root:

```bash
# No OpenAI key needed: health + invalid PDF checks
python3 backend/tests/smoke_api.py --skip-ai

# Real PDF -> AI -> JSON (requires a configured API key and network)
python3 backend/tests/smoke_api.py --pdf demo_samples/waterloo_lease_2pages.pdf
```

The real AI test **exits with a failure code** on any non-200 HTTP response or missing required JSON fields. `--skip-ai` explicitly reports that AI analysis was not tested. The demo sample is a 2-page excerpt from the Waterloo December 1, 2025 council packet; the original 217-page packet exceeds the 25-page limit.

## Secrets

Set `OPENAI_API_KEY` in your terminal environment before launching, or use `backend/.env` **only if** the backend actually loads dotenv. Never commit or share API keys.

## Clean up tracked wrong paths and caches

Check the branch before removal. If these files are tracked in the wrong place, run from repository root:

```bash
git rm -f --ignore-unmatch backend/app/run_backend_mac.sh backend/app/smoke_api.py backend/app/smoke_api.cpython-313.pyc
# For any other tracked Python caches:
git ls-files | grep -E '(^|/)__pycache__/|\.pyc$'
# Remove only the tracked cache paths printed above, e.g. git rm --cached path/to/file.pyc
```

Append these patterns to your **existing** `.gitignore` if absent; do not replace its other rules:

```
__pycache__/
*.py[cod]
.venv/
backend/.venv/
.env
backend/.env
```

## Validation before PR

```bash
bash -n run_backend_mac.sh
python3 -m py_compile backend/tests/smoke_api.py
# If installed in backend environment:
cd backend && .venv/bin/python -m pytest -v
```

`py_compile` creates `__pycache__` locally; it must not be committed. Record actual commands and outputs in the PR description. Do not claim end-to-end success without running the real AI test.
