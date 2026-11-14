# Architecture and design decisions

## Component flow (simplified component diagram)

```mermaid
flowchart LR
  R[Resident] --> UI[React frontend]
  UI --> API[FastAPI POST /analyze]
  API --> PDF[PyMuPDF text extraction]
  PDF --> AI[AI analysis service]
  AI --> VAL[Evidence validator]
  VAL --> API
  API --> UI
```

## Data contract

DecisionAnalysis includes document_title, summary, proposed_changes, affected_groups, potential_benefits, potential_tradeoffs, participation, and unknowns. Findings use page-numbered exact excerpts.

## Trade-offs

- **Text PDFs first:** fewer moving parts than OCR, but excludes scanned documents.
- **Page quotes over AI prose alone:** provides auditability, but exact quotes do not guarantee correct interpretation.
- **No database:** speeds MVP development, but there is no history or search functionality.
- **Server-side API key:** avoids shipping secrets to browsers.
- **Municipality-agnostic fields:** makes the same pipeline usable with different city documents without writing one-off policy logic.

## Scaling later

Add ingestion adapters per city (official agenda/PDF URLs), a document store, human review, scheduled refreshes, and filtering by region. Validate policy-specific claims against authoritative sources before publication.

## Sequence (analysis request)

```mermaid
sequenceDiagram
  participant User
  participant UI as React
  participant API as FastAPI
  participant Parser as PDF parser
  participant Model as AI API
  User->>UI: Upload public PDF
  UI->>API: POST /analyze
  API->>Parser: Extract pages
  Parser-->>API: Text + page indices
  API->>Model: Request structured analysis
  Model-->>API: Findings + evidence
  API->>API: Validate cited excerpts
  API-->>UI: Structured response or clear error
  UI-->>User: Summary and uncertainties
```
