# Sample municipal decisions

Use 2–3 publicly available, text-based municipal PDFs covering distinct topics:
1. Road infrastructure or cycling proposal
2. Zoning / housing planning proposal
3. Public facilities / services proposal

Record title, municipality, official link, access date, and license or permitted use before sharing.
Prefer official municipal links instead of committing copied PDFs.
Do not commit private documents or fabricated source data.

## Evaluation set

`manifest.json` lists each document: `id`, `title`, `municipality`, `category`, official `url`, the `file` name under `pdfs/` (kept local, ignored by git), and `expect`. To set up, download each `url` and save it in `pdfs/` under the listed `file` name.

`pages` is optional: `[first, last]`, 1-based and inclusive, analyzes one report inside a larger PDF such as a council packet, so no separate excerpt has to be shared. Page numbers in the result then count from the first selected page.

`expect` holds:

- `must_include`: phrases the analysis has to mention, such as a key amount or date.
- `must_not_include`: phrases it must not contain, such as "approved" for a proposal that is not approved.
- `participation_must_be_empty`: true when the document only describes past consultation, or none.

Aim for at least one document per topic above, one that only describes past consultation, and one longer than 25 pages. See `docs/testing.md` for how to run it.
