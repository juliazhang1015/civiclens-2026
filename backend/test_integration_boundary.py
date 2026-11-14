"""Isolated HTTP-boundary tests; never contact the OpenAI service."""

import fitz
from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


def make_pdf(text="A proposed municipal sidewalk improvement.", *, encrypted=False):
    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text)
    if encrypted:
        data = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="secret", user_pw="secret")
    else:
        data = doc.tobytes()
    doc.close()
    return data


def upload(data, filename="sample.pdf", mime="application/pdf"):
    return client.post("/analyze", files={"file": (filename, data, mime)})


def assert_error(response, status):
    assert response.status_code == status, response.text
    assert isinstance(response.json().get("detail"), str)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_empty_upload():
    assert_error(upload(b""), 400)


def test_non_pdf_type():
    assert_error(upload(b"hello", "notes.txt", "text/plain"), 415)


def test_invalid_pdf():
    assert_error(upload(b"%PDF-not-a-pdf"), 400)


def test_oversize_pdf():
    assert_error(upload(b"%PDF-" + b" " * (main.MAX_FILE_SIZE + 1)), 400)


def test_encrypted_pdf():
    assert_error(upload(make_pdf(encrypted=True)), 400)


def test_no_selectable_text():
    assert_error(upload(make_pdf(text="")), 400)


def test_page_limit():
    doc = fitz.open()
    for _ in range(26):
        doc.new_page()
    data = doc.tobytes()
    doc.close()
    assert_error(upload(data), 400)


def test_missing_key(monkeypatch):
    async def fail(pages):
        assert isinstance(pages, list) and pages[0].strip()
        raise RuntimeError("OPENAI_API_KEY is not configured. Set it in backend/.env and restart the backend.")
    monkeypatch.setattr(main, "analyze_pages", fail)
    r = upload(make_pdf())
    assert_error(r, 503)
    assert "OPENAI_API_KEY" in r.json()["detail"]


def test_timeout(monkeypatch):
    async def fail(pages):
        raise TimeoutError("Sensitive internal details")
    monkeypatch.setattr(main, "analyze_pages", fail)
    r = upload(make_pdf())
    assert_error(r, 504)
    assert "Sensitive" not in r.text


def test_text_limit(monkeypatch):
    async def fail(pages):
        raise ValueError("This document contains too much text. Upload a shorter document.")
    monkeypatch.setattr(main, "analyze_pages", fail)
    assert_error(upload(make_pdf()), 413)


def test_bad_evidence_is_not_exposed(monkeypatch):
    async def fail(pages):
        raise ValueError("AI returned a quote that could not be matched to the source PDF.")
    monkeypatch.setattr(main, "analyze_pages", fail)
    r = upload(make_pdf())
    assert_error(r, 422)
    assert "quote" not in r.text.lower()


def test_unexpected_runtime_does_not_leak(monkeypatch):
    async def fail(pages):
        raise RuntimeError("provider-secret=never-show-this")
    monkeypatch.setattr(main, "analyze_pages", fail)
    r = upload(make_pdf())
    assert_error(r, 503)
    assert "never-show-this" not in r.text


def test_successful_pipeline(monkeypatch):
    async def fake_analysis(pages):
        assert "sidewalk" in pages[0]
        quote = "A proposed municipal sidewalk improvement."
        return {
            "document_title": "Test municipal document",
            "summary": {"text": "A sidewalk may improve.", "evidence": [{"page": 1, "quote": quote}]},
            "proposed_changes": [], "affected_groups": [], "potential_benefits": [],
            "potential_tradeoffs": [], "participation": [], "unknowns": [],
        }
    monkeypatch.setattr(main, "analyze_pages", fake_analysis)
    r = upload(make_pdf())
    assert r.status_code == 200, r.text
    assert r.json()["summary"]["evidence"][0]["page"] == 1
    assert set(r.json()) == {"document_title", "summary", "proposed_changes", "affected_groups", "potential_benefits", "potential_tradeoffs", "participation", "unknowns"}
