"""Sustained provider outage handling in curate._generate (issue #82).

The primary model keeps its bounded retries. Only when those are exhausted on a
transient error (429/500/503) does the labelled degraded fallback run; other
errors are never masked, and every attempt is visible in the evidence ledger.
"""

from __future__ import annotations

import datetime as dt
import importlib
import logging
from types import SimpleNamespace

import pytest

from src import config
from src.editorial_provenance import EditionEvidence, activate, deactivate

TODAY = dt.date(2026, 10, 20)
WHEN = dt.datetime(2026, 10, 20, 10, 0, tzinfo=dt.timezone.utc)


@pytest.fixture
def curate(monkeypatch):
    module = importlib.import_module("src.curate")

    class ProviderError(Exception):
        def __init__(self, code):
            super().__init__(f"provider {code}")
            self.code = code

    monkeypatch.setattr(module.genai_errors, "APIError", ProviderError)
    monkeypatch.setattr(module.time, "sleep", lambda _s: None)
    monkeypatch.setattr(config, "CURATE_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(config, "CURATE_FALLBACK_MODEL", "gemini-2.5-flash-lite")
    module.ProviderError = ProviderError
    return module


def _model(curate, failing: dict[str, int | None]):
    """A fake client: models listed in ``failing`` raise that status code."""
    calls: list[str] = []

    class Model:
        def generate_content(self, *, model, contents, config):
            calls.append(model)
            code = failing.get(model)
            if code:
                raise curate.ProviderError(code)
            return SimpleNamespace(text='{"sections":[]}', model_version=model, usage_metadata=None)

    return SimpleNamespace(models=Model()), calls


def _run(curate, client, retries=3):
    recorder = EditionEvidence(when=WHEN)
    token = activate(recorder)
    try:
        response = curate._generate(client, "[]", TODAY, retries=retries)
    finally:
        deactivate(token)
    return response, recorder


def test_sustained_503_falls_back_to_the_labelled_degraded_model(curate, caplog):
    client, calls = _model(curate, {"gemini-2.5-flash": 503})

    with caplog.at_level(logging.WARNING, logger="the-daily.curate"):
        response, recorder = _run(curate, client)

    assert response.model_version == "gemini-2.5-flash-lite"
    assert calls == ["gemini-2.5-flash"] * 4 + ["gemini-2.5-flash-lite"]
    assert any("DEGRADED" in r.message and "gemini-2.5-flash-lite" in r.message for r in caplog.records)
    assert [a["fallback"] for a in recorder.attempts][-1] is True
    assert recorder.attempts[-1]["requested_model"] == "gemini-2.5-flash"
    assert recorder.attempts[-1]["actual_model"] == "gemini-2.5-flash-lite"
    assert [a["provider_status"] for a in recorder.attempts[:4]] == [503] * 4


def test_transient_failure_that_recovers_never_uses_the_fallback(curate):
    state = {"n": 0}

    class Model:
        def generate_content(self, *, model, contents, config):
            state["n"] += 1
            if state["n"] == 1:
                raise curate.ProviderError(503)
            return SimpleNamespace(text="{}", model_version=model, usage_metadata=None)

    response, recorder = _run(curate, SimpleNamespace(models=Model()))

    assert response.model_version == "gemini-2.5-flash"
    assert [a["fallback"] for a in recorder.attempts] == [False, False]


@pytest.mark.parametrize("code", [400, 401, 403, 404])
def test_non_transient_errors_are_not_masked_by_the_fallback(curate, code):
    client, calls = _model(curate, {"gemini-2.5-flash": code})

    with pytest.raises(curate.ProviderError):
        _run(curate, client)

    assert calls == ["gemini-2.5-flash"]


def test_both_models_exhausted_raises_the_last_error(curate):
    client, calls = _model(curate, {"gemini-2.5-flash": 503, "gemini-2.5-flash-lite": 503})

    with pytest.raises(curate.ProviderError) as info:
        _run(curate, client, retries=1)

    assert info.value.code == 503
    assert calls == ["gemini-2.5-flash"] * 2 + ["gemini-2.5-flash-lite"] * 2


def test_empty_fallback_setting_disables_the_degraded_path(curate, monkeypatch):
    monkeypatch.setattr(config, "CURATE_FALLBACK_MODEL", "")
    client, calls = _model(curate, {"gemini-2.5-flash": 503})

    with pytest.raises(curate.ProviderError):
        _run(curate, client, retries=1)

    assert calls == ["gemini-2.5-flash"] * 2


def test_fallback_equal_to_primary_is_not_tried_twice(curate, monkeypatch):
    monkeypatch.setattr(config, "CURATE_FALLBACK_MODEL", "gemini-2.5-flash")
    client, calls = _model(curate, {"gemini-2.5-flash": 503})

    with pytest.raises(curate.ProviderError):
        _run(curate, client, retries=0)

    assert calls == ["gemini-2.5-flash"]
