import asyncio
import json

import fitz

from app.schemas import DecisionAnalysis
from evaluation import run as evaluation


def analysis(participation=False) -> DecisionAnalysis:
    finding = {"text": "The lease costs $12,000 per year.", "evidence": [{"page": 1, "quote": "$12,000 per year"}]}
    return DecisionAnalysis(document_title="Lease", summary=finding, proposed_changes=[finding],
                            affected_groups=[], potential_benefits=[], potential_tradeoffs=[],
                            participation=[finding] if participation else [], unknowns=[])


def test_checks_report_missing_and_forbidden_content():
    expect = {"must_include": ["$12,000", "December 31, 2028"], "must_not_include": ["approved"],
              "participation_must_be_empty": True}
    checks = dict(evaluation.run_checks(analysis(participation=True), expect))
    assert checks == {
        'mentions "$12,000"': True,
        'mentions "December 31, 2028"': False,
        'does not say "approved"': True,
        "lists no participation step": False,
    }


def test_checks_ignore_case_and_whitespace():
    assert dict(evaluation.run_checks(analysis(), {"must_include": ["the  LEASE costs"]})) == {
        'mentions "the  LEASE costs"': True}


def test_evaluate_document_records_result_and_failures(tmp_path, monkeypatch):
    with fitz.open() as pdf:
        pdf.new_page().insert_text((72, 72), "The lease costs $12,000 per year.")
        (tmp_path / "lease.pdf").write_bytes(pdf.tobytes())
    entry = {"id": "lease", "title": "Lease", "file": "lease.pdf", "expect": {"must_include": ["$12,000"]}}

    async def ok(pages):
        return analysis()
    monkeypatch.setattr(evaluation, "analyze_pages", ok)
    record = asyncio.run(evaluation.evaluate_document(entry, tmp_path))
    assert record["status"] == "ok" and record["pages"] == 1
    assert record["checks"] == [['mentions "$12,000"', True]]
    assert record["analysis"]["document_title"] == "Lease"

    async def fail(pages):
        raise ValueError("too much text")
    monkeypatch.setattr(evaluation, "analyze_pages", fail)
    record = asyncio.run(evaluation.evaluate_document(entry, tmp_path))
    assert record["status"] == "error" and record["error"] == "ValueError: too much text"

    record = asyncio.run(evaluation.evaluate_document({**entry, "file": "missing.pdf"}, tmp_path))
    assert record["status"] == "missing"


def test_report_lists_every_finding_for_manual_review():
    record = {"id": "lease", "title": "Lease", "url": "https://example.org/lease.pdf", "category": "facilities",
              "status": "ok", "pages": 2, "chars": 2386, "seconds": 43.2, "unmatched_quotes": 1,
              "checks": [['mentions "$12,000"', True], ["lists no participation step", False]],
              "analysis": json.loads(analysis().model_dump_json())}
    failed = {"id": "plan", "title": "Plan", "status": "error", "error": "InputSizeError: too long", "pages": 80,
              "chars": 250000, "seconds": 0.1, "unmatched_quotes": 0, "checks": []}
    report = evaluation.render_report([record, failed], {"provider": "ollama", "model": "qwen3:4b"})

    assert "ollama / qwen3:4b" in report
    assert "| lease | ok | 2 | 43 s | 2 | 1 | 1/2 |" in report
    assert "| plan | error | 80 |" in report and "InputSizeError: too long" in report
    assert "| Summary | The lease costs $12,000 per year. | p1: “$12,000 per year” |  |" in report
    assert "FAIL lists no participation step" in report
