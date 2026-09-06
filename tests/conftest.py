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


class FakeStore:
    """A ``StateStore`` that can lose a push race, on demand and repeatably.

    ``content`` is "what is on the remote". ``load`` parses it exactly the way
    the real store parses the committed file, so a malformed file behaves in a
    test the way it behaves in production. ``reject`` makes the next N saves
    fail the way a rejected ``git push`` does, and ``on_save`` runs just before
    that decision, which is how a test stages "another run claimed this
    article while we were deciding".
    """

    def __init__(self, content: str | None = None, *, reject: int = 0, on_save=None):
        self.content = content
        self.reject = reject
        self.on_save = on_save
        self.saves: list[str] = []
        self.loads = 0

    def load(self):
        from src.voices.state import WatchState, state_from_text

        self.loads += 1
        if self.content is None:
            return WatchState(cold=True)
        return state_from_text(self.content)

    def save(self, state, message: str) -> bool:
        self.saves.append(message)
        if self.on_save is not None:
            self.on_save(self, state, message)
        if self.reject > 0:
            self.reject -= 1
            return False
        self.content = state.dumps()
        return True

    # -- assertions helpers ------------------------------------------------

    def state(self):
        from src.voices.state import WatchState, state_from_text

        return state_from_text(self.content) if self.content is not None else WatchState(cold=True)

    def statuses(self) -> dict:
        return {key: entry.status for key, entry in self.state().entries.items()}


class FakeNotifier:
    """Records alerts. ``fail_on`` makes matching alerts raise ``NotifyError``."""

    def __init__(self, fail_on=None):
        self.sent: list = []
        self.attempted: list = []
        self.fail_on = fail_on

    def send(self, alert) -> None:
        from src.voices.notify import NotifyError

        self.attempted.append(alert)
        if self.fail_on is not None and self.fail_on(alert):
            raise NotifyError("simulated ntfy failure")
        self.sent.append(alert)

    @property
    def messages(self) -> list[str]:
        return [alert.message for alert in self.sent]


def rss_feed(entries, *, title: str = "Test Publication") -> str:
    """A minimal RSS 2.0 feed. Each entry is a dict of the fields we care about."""
    items = []
    for entry in entries:
        parts = [
            f"<title>{entry['title']}</title>",
            f"<link>{entry['link']}</link>",
            f"<pubDate>{entry.get('published', 'Fri, 05 Sep 2026 12:00:00 +0000')}</pubDate>",
        ]
        if entry.get("author"):
            parts.append(f"<dc:creator>{entry['author']}</dc:creator>")
        if entry.get("guid"):
            parts.append(f"<guid>{entry['guid']}</guid>")
        items.append("<item>" + "".join(parts) + "</item>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>'
        f"<title>{title}</title>" + "".join(items) + "</channel></rss>"
    )


def registry_from(voices: list[dict]):
    """Build a validated registry from inline voice definitions."""
    from src.voices.registry import RegistryError, validate

    registry, problems = validate({"version": 1, "voices": voices})
    if problems:
        raise RegistryError(problems)
    return registry


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
