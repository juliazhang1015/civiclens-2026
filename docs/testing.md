# Test plan (record actual results during the hackathon)

## Automated checks

```bash
cd backend
pytest -q
cd ../frontend
npm run build
```

## Manual checks

| Case | Expected result | Actual | Status |
| --- | --- | --- | --- |
| No file selected | Analyze button disabled | TBD | Not run |
| Non-PDF upload | Clear error | TBD | Not run |
| Scanned PDF | Explains that OCR is not supported | TBD | Not run |
| API key missing | Configuration error, no fake result | TBD | Not run |
| Official road proposal | Relevant changes + page citations | TBD | Not run |
| Official zoning proposal | Same pipeline works; zoning-specific facts | TBD | Not run |
| Official public facility proposal | Same pipeline works | TBD | Not run |
| Unknown or absent public comment deadline | Not confirmed, never fabricated | TBD | Not run |
| Fake/out-of-range AI quote | Reject output as unreliable | TBD | Not run |

## Validation protocol

1. Record source municipality, original URL, access date, proposal stage, document page count.
2. Compare summary, all dates and effects against exact PDF page quotes.
3. Mark each claim correct / partly correct / unsupported.
4. Fix prompts or extraction issues and retest.
5. Document known limitations in the municipal readiness report.

**Caution:** Exact quote matching alone does not prove correctness; a human reviewer still checks meaning and context.

## Model evaluation

`data/sample_decisions/manifest.json` lists the test documents and what each analysis must contain. PDFs go in `data/sample_decisions/pdfs/` (not committed). The script runs each one through the live pipeline with the model set in `backend/.env`:

```bash
cd backend
python -m evaluation.run --manifest ../data/sample_decisions/manifest.json
```

It writes `eval_results/<time>-<model>/report.md` (not committed): time, statement count, unmatched quotes and manifest checks per document, then every statement with its quote and an empty Verdict column for step 3 above. Copy the findings worth keeping into the log below.

### Error log

| Date | Document | Model | Observed | Cause | Fix |
| --- | --- | --- | --- | --- | --- |
| 2026-11-14 | waterloo-lease-2025 | mistral-nemo | Whole analysis rejected (422) | Model ended verbatim quotes with `...` | Quote matcher ignores a leading or trailing ellipsis (#8) |
| 2026-11-14 | waterloo-lease-2025 | mistral-nemo | In-kind lease and utility contribution (page 2) not mentioned | Open | Open |
| 2026-11-14 | waterloo-lease-2025 | mistral-nemo | Uncertainty "Future status of the consultation process" although the report describes no consultation | Open | Open |

## Reliability PR verification

- Local Python suite: **19 passed** (includes three synthetic municipal categories through real PDF extraction and SDK parsing with provider HTTP mocked).
- Local TypeScript/Vite production build: **passed**.
- Browser regression suite: `cd frontend && npm run test:e2e`. Runs desktop and 390px layouts, upload validation, loading lock, evidence links, response validation, error recovery and cancellation. CI uploads screenshots and traces in `browser-test-results`.
- Local browser launch was blocked by the execution environment; use the PR CI result for browser-suite status.
- Live OpenAI analysis: **not run**, no API key available. Official transportation, zoning and facility PDFs: **not yet validated**. Synthetic tests are not a substitute for these acceptance checks.
