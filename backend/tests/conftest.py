import os

import pytest

PROVIDER_SETTINGS = ("AI_PROVIDER", "ANALYSIS_")


@pytest.fixture(autouse=True)
def clean_provider_settings(monkeypatch):
    """Tests must not depend on the developer's backend/.env, which is loaded on import.

    Every provider setting is removed so each test sees the documented defaults and
    sets only what it is about. No real key can reach a test either.
    """
    for name in list(os.environ):
        if name.startswith(("OLLAMA_", "ANTHROPIC_", *PROVIDER_SETTINGS)):
            monkeypatch.delenv(name)
