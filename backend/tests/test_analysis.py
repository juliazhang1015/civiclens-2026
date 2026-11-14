import asyncio
from unittest.mock import AsyncMock
import fitz
import httpx2
import pytest
from fastapi.testclient import TestClient
from anthropic import AsyncAnthropic
from pydantic import ValidationError
from app import analyzer
from app.main import app
from app.pdf_reader import MAX_PAGES, extract_pages, PdfError
from app.schemas import DecisionAnalysis


def decision(quote="A protected cycle lane is proposed.", page=1):
    finding = {"text": quote, "evidence": [{"page": page, "quote": quote}]}
    return DecisionAnalysis(document_title="Test proposal", summary=finding, key_facts=[],
        proposed_changes=[finding], affected_groups=[], potential_benefits=[],
        potential_tradeoffs=[], participation=[], unknowns=["No consultation deadline is stated."])


def pdf_bytes(text, blank_first=False):
    with fitz.open() as pdf:
        if blank_first:
            pdf.new_page()
        pdf.new_page().insert_text((72, 72), text)
        return pdf.tobytes()


@pytest.mark.parametrize("quote", ["", "  "])
def test_empty_evidence_rejected(quote):
    with pytest.raises(ValidationError):
        decision(quote)


@pytest.mark.parametrize("quote,page", [("Invented deadline", 1), ("Source text", 2)])
def test_unsupported_evidence_rejected(quote, page):
    with pytest.raises(ValueError):
        analyzer.verify_evidence(decision(quote, page), ["Source text"])


def test_layout_whitespace_matches_but_words_must_match():
    analyzer.verify_evidence(decision("Public office consultation"), ["Public  ofﬁce\nconsultation"])
    with pytest.raises(ValueError):
        analyzer.verify_evidence(decision("Public office approval"), ["Public office consultation"])


@pytest.mark.parametrize("text,blank_first", [
    ("A protected cycle lane is proposed.", False),
    ("The proposal would permit six storeys.\nCouncil has not approved this amendment.", True),
    ("The library renovation would add an accessible entrance.", False),
])
def test_three_categories_through_api_and_sdk(monkeypatch, text, blank_first):
    # Synthetic fixtures; mock only the external model HTTP boundary.
    content = pdf_bytes(text, blank_first)
    pages = extract_pages(content)
    expected = decision(pages[-1], len(pages))
    def respond(request):
        import json
        payload = json.loads(request.content)
        assert request.headers["x-api-key"] == "test-only"
        assert payload["model"] == "claude-opus-5-5"
        assert payload["output_config"]["format"]["type"] == "json_schema"
        assert payload["output_config"]["format"]["schema"]["additionalProperties"] is False
        assert payload["output_config"]["effort"] == "medium"
        assert payload["fallbacks"] == "default" and "server-side-fallback" in request.headers["anthropic-beta"]
        assert "untrusted SOURCE DATA" in payload["system"]
        assert f"[PDF PAGE {len(pages)}]" in payload["messages"][0]["content"]
        return httpx2.Response(200, json={"id": "msg_test", "type": "message", "role": "assistant",
            "model": "claude-opus-5-5", "content": [{"type": "text", "text": expected.model_dump_json()}],
            "stop_reason": "end_turn", "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}})
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    monkeypatch.delenv("ANTHROPIC_EFFORT", raising=False)
    monkeypatch.setattr(analyzer, "AsyncAnthropic", lambda **kwargs: AsyncAnthropic(**kwargs, http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(respond))))
    response = TestClient(app).post("/analyze", files={"file": ("proposal.pdf", content, "application/pdf")})
    assert response.status_code == 200
    assert response.json()["summary"]["evidence"][0]["page"] == len(pages)
    assert response.json()["participation"] == []
    if blank_first:
        assert "no extractable text" in response.json()["unknowns"][-1]


def test_no_silent_truncation(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only")
    monkeypatch.delenv("ANTHROPIC_MAX_TEXT_CHARS", raising=False)
    with pytest.raises(ValueError, match="too much text"):
        asyncio.run(analyzer.analyze_pages(["a" * (analyzer.MAX_TEXT_CHARS + 1)]))


def test_missing_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    response = TestClient(app).post("/analyze", files={"file": ("test.pdf", pdf_bytes("Public proposal"), "application/pdf")})
    assert response.status_code == 503


@pytest.mark.parametrize("kind", ["scanned", "encrypted", "too_many_pages", "oversize"])
def test_pdf_limits(kind):
    with fitz.open() as pdf:
        for _ in range(MAX_PAGES + 1 if kind == "too_many_pages" else 1):
            pdf.new_page()
        data = pdf.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="password") if kind == "encrypted" else pdf.tobytes()
    if kind == "oversize":
        data = b"%PDF-" + b"x" * (10 * 1024 * 1024)
    with pytest.raises(PdfError):
        extract_pages(data)


@pytest.mark.parametrize("failure,status", [(TimeoutError(), 504), (ValueError("secret internal detail"), 422)])
def test_safe_errors(monkeypatch, failure, status):
    monkeypatch.setattr("app.main.analyze_pages", AsyncMock(side_effect=failure))
    response = TestClient(app).post("/analyze", files={"file": ("test.pdf", pdf_bytes("Public proposal"), "application/pdf")})
    assert response.status_code == status
    assert "secret internal detail" not in response.text
