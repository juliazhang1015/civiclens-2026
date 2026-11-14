import asyncio
import json

import fitz
import pytest

from app.schemas import DecisionAnalysis
from evaluation import run as evaluation


def analysis(participation=False) -> DecisionAnalysis:
    finding = {"text": "The lease costs $12,000 per year.", "evidence": [{"page": 1, "quote": "$12,000 per year"}]}
    return DecisionAnalysis(document_title="Lease", summary=finding, key_facts=[], proposed_changes=[finding],
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


def write_pdf(path, *page_texts):
    with fitz.open() as pdf:
        for text in page_texts:
            pdf.new_page().insert_text((72, 72), text)
        path.write_bytes(pdf.tobytes())


def test_entry_can_take_a_page_range_from_a_larger_pdf(tmp_path, monkeypatch):
    # A report inside a council packet: no separate excerpt file has to be passed around.
    write_pdf(tmp_path / "packet.pdf", "Agenda.", "The lease costs $12,000 per year.", "Signatures.", "Other item.")
    seen = []

    async def model(pages):
        seen.append(pages)
        return analysis()
    monkeypatch.setattr(evaluation, "analyze_pages", model)
    entry = {"id": "lease", "title": "Lease", "file": "packet.pdf", "pages": [2, 3]}
    record = asyncio.run(evaluation.evaluate_document(entry, tmp_path))

    assert seen == [["The lease costs $12,000 per year.", "Signatures."]]
    assert record["status"] == "ok" and record["pages"] == 2 and record["page_range"] == [2, 3]
    assert "pages 2–3 of packet.pdf" in evaluation.render_report([record], {"provider": "p", "model": "m"})


@pytest.mark.parametrize("pages", [[0, 2], [3, 2], [2, 9], [2], "2-3"])
def test_page_range_outside_the_pdf_is_an_error_not_a_guess(tmp_path, monkeypatch, pages):
    write_pdf(tmp_path / "packet.pdf", "One.", "Two.", "Three.")

    async def model(pages):
        raise AssertionError("the model must not be called")
    monkeypatch.setattr(evaluation, "analyze_pages", model)
    record = asyncio.run(evaluation.evaluate_document({"id": "x", "file": "packet.pdf", "pages": pages}, tmp_path))
    assert record["status"] == "error" and "pages" in record["error"]


def test_main_writes_results_and_reports_success(tmp_path, monkeypatch, capsys):
    (tmp_path / "pdfs").mkdir()
    write_pdf(tmp_path / "pdfs" / "lease.pdf", "The lease costs $12,000 per year.")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"documents": [
        {"id": "lease", "title": "Lease", "file": "lease.pdf", "expect": {"must_include": ["$12,000"]}},
        {"id": "gone", "title": "Gone", "file": "gone.pdf"}]}))

    async def model(pages):
        return analysis()
    monkeypatch.setattr(evaluation, "analyze_pages", model)
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "test:model")

    assert evaluation.main(["--manifest", str(manifest), "--out", str(tmp_path / "out")]) == 0
    (run_dir,) = (tmp_path / "out").iterdir()
    assert run_dir.name.endswith("-test-model")
    results = json.loads((run_dir / "results.json").read_text())
    assert [d["status"] for d in results["documents"]] == ["ok", "missing"]
    assert "| lease | ok |" in (run_dir / "report.md").read_text()
    assert "gone ... missing" in capsys.readouterr().out

    assert evaluation.main(["--manifest", str(manifest), "--out", str(tmp_path / "out2"), "--only", "lease"]) == 0


def test_main_fails_when_no_document_was_analyzed(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"documents": [{"id": "gone", "title": "Gone", "file": "gone.pdf"}]}))
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    assert evaluation.main(["--manifest", str(manifest), "--out", str(tmp_path / "out")]) == 1
    assert evaluation.main(["--manifest", str(manifest), "--out", str(tmp_path / "out"), "--only", "nothing"]) == 1
