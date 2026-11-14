import asyncio
import json
from types import SimpleNamespace

import pytest

from app import analyzer


def test_ollama_works_without_paid_api_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
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
                "key_facts": [],
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


def test_anthropic_provider_requires_explicit_api_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="requires ANTHROPIC_API_KEY"):
        asyncio.run(analyzer.analyze_pages(["A zoning change is proposed."]))


def test_unknown_provider_rejected(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "unsupported")
    with pytest.raises(RuntimeError, match="AI_PROVIDER"):
        asyncio.run(analyzer.analyze_pages(["An example."]))


def test_ollama_not_running_is_reported_as_unreachable(monkeypatch):
    # The ollama client raises the builtin ConnectionError, not an httpx error.
    monkeypatch.setenv("AI_PROVIDER", "ollama")

    class DownClient:
        def __init__(self, host, timeout):
            pass

        async def chat(self, **kwargs):
            raise ConnectionError("Failed to connect to Ollama.")

    monkeypatch.setattr(analyzer, "AsyncClient", DownClient)
    with pytest.raises(RuntimeError, match="Cannot reach Ollama"):
        asyncio.run(analyzer.analyze_pages(["A zoning change is proposed."]))


class FakeMessages:
    def __init__(self, reply, calls):
        self.reply, self.calls = reply, calls

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        return self.reply


def fake_anthropic(monkeypatch, stop_reason="end_turn", parsed="parsed"):
    calls = []
    reply = SimpleNamespace(stop_reason=stop_reason, parsed_output=parsed)

    class FakeClient:
        def __init__(self, **kwargs):
            self.messages = FakeMessages(reply, calls)
            self.beta = SimpleNamespace(messages=FakeMessages(reply, calls))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setattr(analyzer, "AsyncAnthropic", FakeClient)
    return calls


def test_anthropic_fallback_is_only_sent_to_models_that_accept_it(monkeypatch):
    calls = fake_anthropic(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
    monkeypatch.setenv("ANTHROPIC_EFFORT", "")
    assert asyncio.run(analyzer._call_model("system", "user", analyzer.DecisionAnalysis)) == "parsed"
    assert "fallbacks" not in calls[0] and "betas" not in calls[0] and "output_config" not in calls[0]

    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-5-5")
    monkeypatch.setenv("ANTHROPIC_EFFORT", "low")
    asyncio.run(analyzer._call_model("system", "user", analyzer.DecisionAnalysis))
    assert calls[1]["fallbacks"] == "default" and calls[1]["output_config"] == {"effort": "low"}
    assert calls[1]["system"] == "system" and calls[1]["output_format"] is analyzer.DecisionAnalysis


@pytest.mark.parametrize("stop_reason,parsed", [("refusal", None), ("max_tokens", None), ("max_tokens", "partial")])
def test_anthropic_refusal_or_cut_off_reply_is_not_used(monkeypatch, stop_reason, parsed):
    fake_anthropic(monkeypatch, stop_reason, parsed)
    with pytest.raises(ValueError):
        asyncio.run(analyzer._call_model("system", "user", analyzer.DecisionAnalysis))
