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
| 2026-11-14 | waterloo-lease-2025 | mistral-nemo | In-kind lease and utility contribution (page 2) not mentioned | Prompt did not ask for financial sections | Prompt asks for amounts, who pays and specific open questions. **Not reliably fixed:** raised as an open question in one run, missing again in the next |
| 2026-11-14 | waterloo-lease-2025 | mistral-nemo | Uncertainty "Future status of the consultation process" although the report describes no consultation | Prompt allowed generic unknowns | Prompt asks for specific questions only; not seen in the next run |
| 2026-11-14 | waterloo-lease-2025 | mistral-nemo | Lease from January 1, 2026 to December 31, 2028 described as "two years and six months", later "two years" | Model does date arithmetic wrongly; the quote matches, so verification cannot catch it | Prompt forbids calculating durations. **Still occurs.** Needs a stronger model or a check on durations |
| 2026-11-14 | waterloo-lease-2025 | mistral-nemo | Lease space listed as a key "amount" | Model misfiled a place | Key facts without a digit are dropped |
| 2026-11-14 | waterloo-lease-2025 (forced into 2 parts) | mistral-nemo | Merged title "Municipal Document Overview"; same group listed twice; open question from page 2 lost | Merge step never sees the cover page; near-duplicate wording; model returned no open questions | Title taken from the first part; duplicates ignore a leading "the" and final period; open questions fall back to the parts' own |
| 2026-11-14 | waterloo-lease-2025 (forced into 2 parts) | mistral-nemo | Part 2 analyzed the cover page again and reported nothing from page 2 | The whole first page was repeated in each part as context | Parts get a 300-character header marked as context, and may cite only their own pages |
| 2026-11-14 | waterloo-lease-2025 | mistral-nemo | Whole analysis rejected (422) | Summary quote joined two real passages with `...` | A joined quote is split into separate excerpts, each checked on the page |
| 2026-11-14 | waterloo-lease-2025 | mistral-nemo | Lease term filed as a key "amount" | Model picks the wrong kind | Open; the value itself is verbatim |

## Reliability PR verification

- Local Python suite: **19 passed** (includes three synthetic municipal categories through real PDF extraction and SDK parsing with provider HTTP mocked).
- Local TypeScript/Vite production build: **passed**.
- Browser regression suite: `cd frontend && npm run test:e2e`. Runs desktop and 390px layouts, upload validation, loading lock, evidence links, response validation, error recovery and cancellation. CI uploads screenshots and traces in `browser-test-results`.
- Local browser launch was blocked by the execution environment; use the PR CI result for browser-suite status.
- Live OpenAI analysis: **not run**, no API key available (the OpenAI provider has since been replaced by Anthropic; see Model evaluation above). Official transportation, zoning and facility PDFs: **not yet validated**. Synthetic tests are not a substitute for these acceptance checks.
