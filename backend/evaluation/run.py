"""Run real municipal PDFs through the live analysis pipeline and write a review report.

    cd backend
    python -m evaluation.run --manifest ../data/sample_decisions/manifest.json

The model is whatever backend/.env selects. Automatic checks only catch what the
manifest spells out; every statement still needs a human verdict in the report.
"""
import argparse
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from app.analyzer import FINDING_CATEGORIES, ai_provider, analyze_pages
from app.pdf_reader import extract_pages
from app.schemas import DecisionAnalysis

SECTION_TITLES = {"summary": "Summary", "key_facts": "Key fact", "proposed_changes": "Proposed", "affected_groups": "Affected",
                  "potential_benefits": "Benefit", "potential_tradeoffs": "Trade-off",
                  "participation": "Participation"}


class UnmatchedQuoteCounter(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.count = 0

    def emit(self, record):
        self.count += "Unmatched quote" in record.getMessage()


def squash(text: str) -> str:
    return " ".join(text.lower().split())


def run_checks(result: DecisionAnalysis, expect: dict) -> list[tuple[str, bool]]:
    """Manifest expectations against the analysis text shown to residents (not the quotes)."""
    findings = [result.summary, *(f for c in FINDING_CATEGORIES for f in getattr(result, c))]
    facts = (f"{fact.value} {fact.label}" for fact in result.key_facts)
    shown = squash(" ".join([result.document_title, *(f.text for f in findings), *facts, *result.unknowns]))
    checks = [(f'mentions "{phrase}"', squash(phrase) in shown) for phrase in expect.get("must_include", [])]
    checks += [(f'does not say "{phrase}"', squash(phrase) not in shown)
               for phrase in expect.get("must_not_include", [])]
    if expect.get("participation_must_be_empty"):
        checks.append(("lists no participation step", not result.participation))
    return checks


def select_pages(pages: list[str], page_range) -> list[str]:
    """`[first, last]`, 1-based and inclusive: one report inside a larger PDF such as a council packet.

    Page numbers in the analysis then count from the first selected page.
    """
    valid = (isinstance(page_range, list) and len(page_range) == 2
             and all(isinstance(n, int) for n in page_range) and 1 <= page_range[0] <= page_range[1] <= len(pages))
    if not valid:
        raise ValueError(f"pages must be [first, last] within 1-{len(pages)}, got {page_range!r}")
    return pages[page_range[0] - 1:page_range[1]]


async def evaluate_document(entry: dict, pdf_dir: Path) -> dict:
    record = {**{k: entry.get(k) for k in ("id", "title", "url", "category")},
              "status": "missing", "pages": 0, "chars": 0, "seconds": 0.0, "unmatched_quotes": 0, "checks": []}
    path = pdf_dir / entry["file"]
    if not path.is_file():
        record["error"] = f"PDF not found: {path}"
        return record

    counter = UnmatchedQuoteCounter()
    logger = logging.getLogger("app.analyzer")
    logger.addHandler(counter)
    start = time.monotonic()
    try:
        pages = extract_pages(path.read_bytes())
        if "pages" in entry:
            pages = select_pages(pages, entry["pages"])
            record["page_range"] = list(entry["pages"])
            record["file"] = entry["file"]
        record.update(pages=len(pages), chars=sum(map(len, pages)))
        result = await analyze_pages(pages)
        record.update(status="ok", analysis=json.loads(result.model_dump_json()),
                      checks=[list(check) for check in run_checks(result, entry.get("expect", {}))])
    except Exception as exc:  # a failed document is a result, not a reason to stop the run
        record.update(status="error", error=f"{type(exc).__name__}: {exc}")
    finally:
        logger.removeHandler(counter)
        record.update(seconds=round(time.monotonic() - start, 1), unmatched_quotes=counter.count)
    return record


def cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def render_report(records: list[dict], run: dict) -> str:
    lines = [f"# Evaluation run: {run['provider']} / {run['model']}", "",
             "Fill in the Verdict column by hand: correct / partly / unsupported. Quote matching "
             "only proves the quote is in the PDF, not that the statement follows from it.", "",
             "| Document | Status | Pages | Time | Statements | Unmatched quotes | Checks passed |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in records:
        analysis = r.get("analysis")
        statements = 1 + sum(len(analysis[c]) for c in ("key_facts", *FINDING_CATEGORIES)) if analysis else 0
        passed = f"{sum(ok for _, ok in r['checks'])}/{len(r['checks'])}" if r["checks"] else "–"
        lines.append(f"| {r['id']} | {r['status']} | {r['pages']} | {r['seconds']:.0f} s | {statements} | "
                     f"{r['unmatched_quotes']} | {passed} |")
    for r in records:
        lines += ["", f"## {r['id']}: {cell(r.get('title') or '')}", ""]
        if r.get("url"):
            lines += [f"Source: {r['url']} ({r.get('category') or 'uncategorised'}, {r['chars']} characters)", ""]
        if r.get("page_range"):
            first, last = r["page_range"]
            lines += [f"Analyzed pages {first}\u2013{last} of {r['file']}; page numbers below count from page {first}.", ""]
        if r["status"] != "ok":
            lines.append(f"**{r['status']}**: {cell(r.get('error', ''))}")
            continue
        lines += [f"- {'PASS' if ok else 'FAIL'} {name}" for name, ok in r["checks"]]
        lines += ["", "| Section | Statement | Evidence | Verdict |", "| --- | --- | --- | --- |"]
        analysis = r["analysis"]
        key_facts = [{"text": f"{fact['value']}: {fact['label']}", "evidence": fact["evidence"]}
                     for fact in analysis["key_facts"]]
        for section in ("summary", "key_facts", *FINDING_CATEGORIES):
            findings = {"summary": [analysis["summary"]], "key_facts": key_facts}.get(section) or analysis[section]
            for finding in findings:
                evidence = "; ".join(f"p{ev['page']}: “{cell(ev['quote'])}”" for ev in finding["evidence"])
                lines.append(f"| {SECTION_TITLES[section]} | {cell(finding['text'])} | {evidence} |  |")
        if analysis["unknowns"]:
            lines += ["", "Uncertainties reported:"] + [f"- {cell(u)}" for u in analysis["unknowns"]]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Returns 0 when at least one document was analyzed, 1 when none was."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pdf-dir", type=Path, help="defaults to pdfs/ next to the manifest")
    parser.add_argument("--out", type=Path, default=Path("../eval_results"))
    parser.add_argument("--only", nargs="*", help="document ids to run")
    args = parser.parse_args(argv)

    entries = json.loads(args.manifest.read_text())["documents"]
    if args.only:
        entries = [entry for entry in entries if entry["id"] in args.only]
    pdf_dir = args.pdf_dir or args.manifest.parent / "pdfs"
    provider = ai_provider()
    model = os.getenv("OLLAMA_MODEL", "qwen3:4b") if provider == "ollama" else os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5")
    run = {"provider": provider, "model": model, "started": datetime.now().isoformat(timespec="seconds")}

    records = []
    for entry in entries:
        print(f"{entry['id']} ...", end=" ", flush=True)
        record = asyncio.run(evaluate_document(entry, pdf_dir))
        print(record["status"], f"{record['seconds']:.0f}s", record.get("error", ""))
        records.append(record)

    out = args.out / f"{run['started'].replace(':', '')}-{model.replace(':', '-').replace('/', '-')}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps({"run": run, "documents": records}, indent=1, ensure_ascii=False))
    (out / "report.md").write_text(render_report(records, run))
    print(f"Wrote {out / 'report.md'}")
    if not any(record["status"] == "ok" for record in records):
        print("No document was analyzed. Put the PDFs listed in the manifest in", pdf_dir)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
