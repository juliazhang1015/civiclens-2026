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

## Reliability PR verification

- Local Python suite: **19 passed** (includes three synthetic municipal categories through real PDF extraction and SDK parsing with provider HTTP mocked).
- Local TypeScript/Vite production build: **passed**.
- Browser regression suite: `cd frontend && npm run test:e2e`. Runs desktop and 390px layouts, upload validation, loading lock, evidence links, response validation, error recovery and cancellation. CI uploads screenshots and traces in `browser-test-results`.
- Local browser launch was blocked by the execution environment; use the PR CI result for browser-suite status.
- Live OpenAI analysis: **not run**, no API key available. Official transportation, zoning and facility PDFs: **not yet validated**. Synthetic tests are not a substitute for these acceptance checks.
