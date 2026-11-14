# CivicScope backend CI repair (main-based)

This patch is based on the observed `main` version of `backend/app/main.py` on Nov 14, 2026, **not** the experimental Ollama PR #4 version. Do not overwrite PR #4's `main.py` with it: that branch introduces `InputSizeError` and provider-specific behavior that need a separate integration decision.

Changes:
- Convert analyzer's known `ValueError("This document contains too much text...")` to HTTP 413.
- Sanitize all unexpected RuntimeError messages (HTTP 503).
- Preserve generic HTTP 422 for other ValueErrors and unknown exceptions.
- Always close uploaded files even if file reading fails.
- Leave `/health`, `/analyze`, response schema, PDF validation, and analyzer unchanged.

## Apply to PR #5 or a new branch from main

Copy **only** `backend/app/main.py` and `backend/tests/test_ci_error_regressions.py` into matching paths in the checked-out repo (not `backend/main.py`). Do not upload the patch's folder as an extra nested directory.

```bash
git switch main
git pull origin main
git switch -c fix/backend-ci-boundaries
# Copy the two files into this checkout
cd backend
python -m pip install -r requirements.txt
python -m pytest -q
cd ..
git add backend/app/main.py backend/tests/test_ci_error_regressions.py
git commit -m "Fix backend text-limit status and sanitize runtime errors"
git push -u origin fix/backend-ci-boundaries
```

Alternatively, when updating PR #5, check out `ericzhu0220-patch-1` and put files in the same exact paths; CI tests the commit pushed to that branch, not whatever local folder has a ZIP.

## Important

PR #4 `feature/portable-ollama-backend` has different code (`InputSizeError`) and has already had a regression-fix commit. Do not overwrite it. Coordinate with Julia before merging branches. Verify the GitHub Actions run is attached to the **new commit hash** and that the complete test suite passes; a targeted test pass is not proof of CI success.
