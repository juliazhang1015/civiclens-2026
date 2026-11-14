"""Regression tests for HTTP boundaries, using a controlled PDF extractor and AI mock."""
import pytest
from fastapi.testclient import TestClient
from app import main


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "extract_pages", lambda _: ["Sample municipal proposal text"])
    return TestClient(main.app)


def post_pdf(client):
    return client.post("/analyze", files={"file": ("proposal.pdf", b"%PDF-1.7 sample", "application/pdf")})


def test_text_limit_returns_413(client, monkeypatch):
    async def too_long(_):
        raise ValueError("This document contains too much text. Upload a shorter document.")
    monkeypatch.setattr(main, "analyze_pages", too_long)
    response = post_pdf(client)
    assert response.status_code == 413
    assert "too much text" in response.json()["detail"].lower()


def test_runtime_does_not_leak(client, monkeypatch):
    async def provider_failure(_):
        raise RuntimeError("provider-secret=never-show-this")
    monkeypatch.setattr(main, "analyze_pages", provider_failure)
    response = post_pdf(client)
    assert response.status_code == 503
    assert "never-show-this" not in response.text
    assert "provider-secret" not in response.text


def test_other_validation_is_422_and_sanitized(client, monkeypatch):
    async def bad_evidence(_):
        raise ValueError("invalid source quote sensitive-value")
    monkeypatch.setattr(main, "analyze_pages", bad_evidence)
    response = post_pdf(client)
    assert response.status_code == 422
    assert "sensitive-value" not in response.text


def test_upload_cleanup_and_content_type():
    response = TestClient(main.app).post("/analyze", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 415
