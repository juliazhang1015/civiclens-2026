# MVP requirements

## Primary users

- Residents: understand a proposed municipal decision in plain language.
- Community organizations: explain proposals to their members.
- Municipal staff (secondary): identify gaps in public-facing communication.

## Functional requirements

- FR-01: Accept a text-based municipal PDF (<= 10 MB, <= 25 pages).
- FR-02: Extract text with preserved 1-based page references.
- FR-03: Return a neutral, concise description of a proposal.
- FR-04: Explain potential changes, groups affected, benefits and trade-offs.
- FR-05: Surface explicitly documented participation information.
- FR-06: Provide supporting page excerpts; reject quotations that do not occur in source text.
- FR-07: Indicate unknowns rather than guessing.
- FR-08: Reuse the same flow across at least three types of municipal proposal.

## Non-functional requirements

- NFR-01: No API keys or secrets in the browser or repository.
- NFR-02: Accessible labels and responsive layout.
- NFR-03: Fail with understandable errors when parsing or AI analysis fails.
- NFR-04: No automatic claim that a future event or deadline is current.
- NFR-05: Keep reusable input schema independent of any single municipality.

## Out of scope for first iteration

- Automated scraping of municipal portals
- Login, alerts and persistent user profiles
- Interactive maps or animations without verified geodata
- Scanned PDFs / OCR and document comparison
