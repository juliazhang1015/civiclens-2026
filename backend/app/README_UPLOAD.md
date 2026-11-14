# CivicScope backend run + smoke-test pack

This is an **additive testing pack**, not a replacement backend. It does not overwrite `backend/app/main.py`, `backend/app/analyzer.py`, `backend/app/pdf_reader.py`, or the frontend.

## Put these files in your existing `feature/Backend` repository

Copy `run_backend_mac.sh` and `demo_samples/` to the repository root. Copy `backend/tests/smoke_api.py` into the existing `backend/tests/` folder. Preserve the existing repository's other files.

## Start on macOS

From the repository root:

```bash
chmod +x run_backend_mac.sh
./run_backend_mac.sh
```

Open http://127.0.0.1:8000/docs . In a second terminal at the repository root:

```bash
python3 backend/tests/smoke_api.py --pdf demo_samples/waterloo_lease_2pages.pdf
```

The smoke test verifies `/health`, invalid PDF rejection, and tries a real 2-page PDF. The final request needs a valid API key and access to the OpenAI service for a 200 response. A 503 or 504 does not count as successful end-to-end AI analysis.

## API key

Put `OPENAI_API_KEY=...` in `backend/.env` only if the existing backend explicitly loads dotenv, or export it in your terminal before launching. Never commit `.env` or paste keys into chat.

## Upload to GitHub

```bash
git checkout feature/Backend
git status
git add run_backend_mac.sh backend/tests/smoke_api.py demo_samples/waterloo_lease_2pages.pdf
git commit -m "Add backend run script and API smoke tests"
git push origin feature/Backend
```

Do not commit `.venv`, `.env`, or secrets. Review `git status` before committing. If your team does not want demo PDFs committed, omit the PDF from `git add` and keep it locally.

## Limitations

The test pack is syntax-checked, but cannot establish compatibility with your current GitHub branch until its source files are available. It does not claim the AI API is working. The sample PDF is an excerpt of the uploaded Waterloo Council packet, pages 19–20.
