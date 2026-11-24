"""Offline regression for #110: November 7/10 Gemini v1 developer-instruction 400.

SDK 3 selected /v1 by default in production. Keep the API-version contract
explicit even when the environment requests v1. No provider credentials used.
"""
from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

from src import config, curate


def test_curation_client_explicitly_selects_v1beta(monkeypatch):
    seen = {}

    def fake_client(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(models=SimpleNamespace())

    monkeypatch.setenv("GEMINI_API_KEY", "offline-test-only")
    monkeypatch.setenv("GOOGLE_GENAI_API_VERSION", "v1")
    monkeypatch.setattr(curate.genai, "Client", fake_client)

    client = curate._client()

    assert client.models is not None
    assert seen["api_key"] == "offline-test-only"
    assert seen["http_options"].api_version == "v1beta"


def test_real_curation_shape_uses_compatible_client_and_approved_model(monkeypatch):
    seen = {}
    monkeypatch.setenv("GEMINI_API_KEY", "offline-test-only")
    monkeypatch.setattr(config, "CURATE_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(config, "CURATE_FALLBACK_MODEL", "gemini-2.5-flash-lite")

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            seen["model"] = model
            seen["contents"] = contents
            seen["config"] = config
            if seen["version"] != "v1beta":
                raise AssertionError("v1 developer-instruction request would fail HTTP 400")
            return SimpleNamespace(text='{"sections":[]}', model_version=model, usage_metadata=None)

    def fake_client(*, api_key, http_options):
        seen["version"] = http_options.api_version
        return SimpleNamespace(models=FakeModels())

    monkeypatch.setattr(curate.genai, "Client", fake_client)
    client = curate._client()
    response = curate._generate(client, "[]", dt.date(2026, 11, 10), retries=0)

    assert response.model_version == "gemini-2.5-flash"
    assert seen["contents"] == "[]"
    assert seen["version"] == "v1beta"
    assert seen["config"].system_instruction
    assert seen["config"].response_mime_type == "application/json"
    assert seen["config"].max_output_tokens == config.CURATE_MAX_TOKENS
