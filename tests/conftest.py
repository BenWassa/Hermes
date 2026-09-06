"""Shared test scaffolding for the production-v2 pipeline.

Everything here is offline. Adapters are exercised against recorded provider
fixtures through a fake HTTP client, so the suite proves the same code paths
the live build uses without a network call. Live checking is a separate,
deliberate operator command (``python -m src.voices.audit --live``).
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

UTC = dt.timezone.utc

#: The moment every dated fixture is written relative to.
NOW = dt.datetime(2026, 9, 5, 18, 0, 0, tzinfo=UTC)


def fixture_text(*parts: str) -> str:
    return (FIXTURES.joinpath(*parts)).read_text(encoding="utf-8")


def fixture_bytes(*parts: str) -> bytes:
    return (FIXTURES.joinpath(*parts)).read_bytes()


def fixture_json(*parts: str):
    return json.loads(fixture_text(*parts))


class FakeResponse:
    def __init__(self, *, content: bytes = b"", text: str = "", payload=None, status: int = 200):
        self.content = content or text.encode("utf-8")
        self.text = text or self.content.decode("utf-8", "replace")
        self._payload = payload
        self.status_code = status

    def json(self):
        if self._payload is None:
            return json.loads(self.text)
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHttp:
    """A ``VoiceHttp`` stand-in backed by a URL -> response routing table.

    Routes are matched on a substring of the request URL. A route may be an
    exception instance, which is raised, so "this one source is broken" is as
    easy to set up as "this one source works".
    """

    def __init__(self, routes: dict, budget=None):
        from src.voices.http import RequestBudget

        self.routes = routes
        self.budget = budget or RequestBudget()
        self.calls: list[tuple[str, dict]] = []

    def get(self, url, *, provider, params=None, headers=None):
        self.budget.charge(provider)
        self.calls.append((url, dict(params or {})))
        for pattern, response in self.routes.items():
            if pattern in url:
                if isinstance(response, Exception):
                    raise response
                return response
        raise RuntimeError(f"no fake route for {url}")


@pytest.fixture
def now() -> dt.datetime:
    return NOW


@pytest.fixture
def window():
    from src.voices.window import EditionWindow

    return EditionWindow(since=NOW - dt.timedelta(hours=36), until=NOW)


@pytest.fixture
def acceptance_registry():
    from src.voices import load_registry

    return load_registry(FIXTURES / "voices" / "acceptance.json")


@pytest.fixture
def production_registry():
    from src.voices import load_registry

    return load_registry(Path(__file__).resolve().parents[1] / "data" / "voices.json")
