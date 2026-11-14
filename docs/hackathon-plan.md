# CivicScope: demo readiness and 36-hour plan

## Current audit

Starting point: main at dec145da55f3a81200bf5f2ee9dc0b083119e286.
PRs #1 and #2 are merged. Main's Basic checks workflow passed.
Application branding is CivicScope; the repository remains `juliazhang1015/civiclens-2026`.
The React / FastAPI / PyMuPDF / model-API architecture is appropriate for this scope (the paid provider was later changed from OpenAI to Anthropic).

## Demo blockers, in priority order

1. **Model output contract:** original JSON mode did not provide the required schema. Replaced with the SDK's Pydantic structured-output parser. The model receives a form with exact field names; the API validates the completed form before the UI sees it.
2. **Unproven live model quality:** no live API key is available in the development environment. Three synthetic category fixtures test upload, PDF extraction, actual SDK schema serialization/parsing, evidence validation and API output with the external provider mocked. They do not establish real municipal accuracy. Real official PDFs and an active key are still required.
3. **Silent content loss:** original extraction-to-prompt flow truncated every page to 12,000 characters. Now the complete extracted text is sent, or documents above 100,000 characters are rejected. Blank pages remain in the page index and trigger a coverage warning. Images and tables still need human review.
4. **Unbounded waiting and confusing failures:** provider calls now have a 60-second network timeout, a 75-second overall analysis deadline, no automatic retries, and a 5,000-token output cap. The local Ollama path waits up to 240 seconds per model call. A long document takes one call per part plus one to merge, so the browser waits up to 15 minutes and supports cancellation. Browser cancellation does not guarantee cancellation of an already-running provider call or its cost.
5. **Upload/result mismatch:** file selection is disabled while analyzing; selecting a new file clears old results. Client-side file checks and response-shape validation prevent avoidable failures.
6. **Deployment routing:** Vite's `/api` proxy is a development feature. A static frontend deployment alone cannot serve `/api/analyze`. For the hackathon, use the documented two-terminal local demo or configure an equivalent reverse proxy before deployment.

## First implementation

- Responsive civic UI, keyboard navigation, reduced-motion support and focused result heading.
- Expandable evidence with links to PDF pages in the locally selected file. Page jumps depend on browser PDF viewer support.
- Separate source-based findings from potential impacts; neither is labeled verified truth.
- Whitespace and Unicode-ligature normalization for quote matching. Different words and wrong page numbers still fail.
- Strict required schema fields and non-empty findings/evidence; empty category arrays are valid.
- Provider outage, credential, quota and timeout errors separated from unreliable-analysis errors.
- Frontend lockfile and reproducible `npm ci` in CI.

## Suggested time budget (from team kickoff)

| Hours | Owner | Deliverable / exit criterion |
| --- | --- | --- |
| 0–4 | Julia + Eric | Review and integrate reliability PR; both servers start; CI passes |
| 4–10 | Julia (AI) + Hanson | Run three official PDFs: transportation, zoning, public facilities. Record URL, page count, result, latency and every citation check |
| 10–18 | Julia (frontend) + Eric | Resolve issues from real PDFs, test mobile and keyboard flow; establish demo machine/network/API configuration |
| 18–26 | Hanson + Zoe | Adversarial and error checks; source table; screenshots; architecture explanation; evaluate uncertainty and proposal-vs-approval wording |
| 26–32 | Whole team | Rehearse a 3-minute demo with a primary and backup official document; verify quota and internet |
| 32–36 | Whole team | Feature freeze, fix blockers only, final rehearsal and submission |

Keep OCR, login, scraping, maps and chat out of this iteration. Assign file ownership before simultaneous edits. Use focused branches and review PRs before merging.

## Live acceptance checklist

- Set the API key only in local `backend/.env`. Never paste it into frontend code or a PR.
- Open `/health`, then upload the primary official PDF through the browser.
- Confirm proposed actions are not described as approved decisions.
- Compare every quote and PDF page; check that the interpretation follows from surrounding text.
- Confirm missing deadlines remain unknown and old dates are not advertised as current.
- Repeat for the other two categories and record observations in `docs/testing.md`.
- Test invalid, scanned, mixed text/image, encrypted and overly long PDFs, plus backend unavailable.
- Test keyboard selection, narrow screen, cancellation and a second upload.
- A fallback screenshot or recording must be labeled as a previous run, never presented as a fresh analysis.

## Three-minute demo

1. **0:00–0:25 — Problem:** municipal PDFs contain important decisions but are difficult to explore quickly.
2. **0:25–1:10 — Upload:** select an official document; explain that the same schema supports other municipalities and categories while it loads.
3. **1:10–2:10 — Explore:** show the summary, proposed changes, possible trade-offs, an exact excerpt and its PDF page.
4. **2:10–2:40 — Participation and uncertainty:** show what is stated and what is missing; emphasize that a proposal is not automatically approved.
5. **2:40–3:00 — Architecture:** React displays the analysis; FastAPI extracts PDF pages; the model fills a structured schema; the validator checks quotes before returning results. Human review checks meaning.

Reference: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
