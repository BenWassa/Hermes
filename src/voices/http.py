"""Shared HTTP access for Voice adapters, with a request budget.

Every provider request an adapter makes goes through ``VoiceHttp`` so the run
can account for it. Budgets are the point: Perigon's personal tier is measured
in requests per *month*, so an architecture that quietly scales as
``voices x providers x polls`` is a bug, not a tuning problem. The counter
makes an accidental explosion visible in the logs and in build diagnostics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import requests

log = logging.getLogger("the-daily.voices.http")

USER_AGENT = "TheDaily/2.0 (+https://github.com/BenWassa/Hermes)"
DEFAULT_TIMEOUT = 20


class BudgetExceeded(RuntimeError):
    """A provider's per-run request budget is spent."""


@dataclass
class RequestBudget:
    """Per-provider request allowances for one run."""

    limits: dict[str, int] = field(default_factory=dict)
    spent: dict[str, int] = field(default_factory=dict)

    def charge(self, provider: str) -> None:
        limit = self.limits.get(provider)
        used = self.spent.get(provider, 0)
        if limit is not None and used >= limit:
            raise BudgetExceeded(f"{provider}: per-run budget of {limit} request(s) already spent")
        self.spent[provider] = used + 1

    def report(self) -> dict[str, int]:
        return dict(sorted(self.spent.items()))

    @property
    def total(self) -> int:
        return sum(self.spent.values())


class VoiceHttp:
    """A thin, budgeted GET wrapper. One instance per discovery run."""

    def __init__(self, budget: RequestBudget | None = None, timeout: int = DEFAULT_TIMEOUT,
                 session: requests.Session | None = None):
        self.budget = budget or RequestBudget()
        self.timeout = timeout
        self._session = session or requests.Session()
        self._session.headers.setdefault("User-Agent", USER_AGENT)

    def get(self, url: str, *, provider: str, params: dict | None = None,
            headers: dict | None = None) -> requests.Response:
        self.budget.charge(provider)
        response = self._session.get(url, params=params, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        log.debug("voice http %s %s -> %s", provider, url, response.status_code)
        return response
