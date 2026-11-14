import asyncio
import json
from types import SimpleNamespace

import pytest

from app import analyzer


def test_ollama_works_without_paid_api_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

    class StubClient:
        def __init__(self, host, timeout):
            assert host == "http://127.0.0.1:11434"
            assert timeout > 0

        async def chat(self, **kwargs):
            assert kwargs["model"] == "qwen3:4b"
            assert kwargs["format"]["type"] == "object"
            content = {
                "document_title": "Zoning notice",
                "summary": {
                    "text": "A zoning change is proposed.",
                    "evidence": [{"page": 1, "quote": "A zoning change is proposed."}],
                },
                "proposed_changes": [],
                "affected_groups": [],
                "potential_benefits": [],
                "potential_tradeoffs": [],
                "participation": [],
                "unknowns": [],
            }
            return SimpleNamespace(message=SimpleNamespace(content=json.dumps(content)))

    monkeypatch.setattr(analyzer, "AsyncClient", StubClient)
    result = asyncio.run(analyzer.analyze_pages(["A zoning change is proposed."]))
    assert result.document_title == "Zoning notice"


def test_ollama_rejects_excessively_long_input_without_silent_truncation(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MAX_TEXT_CHARS", "10")
    with pytest.raises(ValueError, match="too much text"):
        asyncio.run(analyzer.analyze_pages(["A document containing more than ten characters"]))


def test_openai_provider_requires_explicit_api_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="requires OPENAI_API_KEY"):
        asyncio.run(analyzer.analyze_pages(["A zoning change is proposed."]))


def test_unknown_provider_rejected(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "unsupported")
    with pytest.raises(RuntimeError, match="AI_PROVIDER"):
        asyncio.run(analyzer.analyze_pages(["An example."]))
