"""Small regression tests for live provider contracts hardened in #13.

These stay deterministic. Live verification is an operator audit, while CI
locks the query shapes that provider documentation says are safe.
"""

from __future__ import annotations

import datetime as dt

from src.voices.adapters import FetchWindow, get_adapter
from src.voices.adapters.base import SourceRequest
from tests.conftest import NOW, FakeHttp, FakeResponse


def test_perigon_free_plan_query_never_exceeds_25_results(monkeypatch):
    monkeypatch.setenv("PERIGON_API_KEY", "test-key")
    adapter = get_adapter("perigon_journalist")
    request = SourceRequest(
        adapter="perigon_journalist",
        label="three journalists",
        source_keys=(
            "perigon_journalist:one",
            "perigon_journalist:two",
            "perigon_journalist:three",
        ),
        payload={"journalist_ids": ["one", "two", "three"]},
    )
    http = FakeHttp({"perigon.io": FakeResponse(payload={"articles": []})})
    window = FetchWindow(since=NOW - dt.timedelta(hours=36), until=NOW)

    assert adapter.fetch(request, http, window) == []
    _url, params = http.calls[0]
    assert params["size"] == 25
