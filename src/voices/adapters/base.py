"""The Voice source adapter contract.

An adapter answers exactly one question: *what has this source published
recently?* It returns ``Observation`` records carrying whatever source-native
authorship evidence exists, and it knows nothing about Voices, aliases, or
attribution. Resolution happens later, once, over every observation from every
adapter, so adding a source can never add a new way to decide authorship.

Three rules hold for every adapter:

* **Never invent attribution.** If the expected structure is missing, return
  nothing and say so. A parser that guesses is worse than a parser that fails.
* **Fail locally.** A dead feed or a 500 from a provider raises
  ``AdapterError``; the orchestrator records it and the rest of the run
  continues.
* **Batch by provider, not by person.** ``plan`` receives every registered
  source of its type at once so it can collapse them into as few provider
  requests as the API allows.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from ..model import Observation


class AdapterError(RuntimeError):
    """A source could not be read. Degrades one source, never the run."""


@dataclass
class SourceRequest:
    """One planned unit of work: some sources served by one provider call."""

    adapter: str
    label: str
    source_keys: tuple[str, ...]
    payload: dict = field(default_factory=dict)


@dataclass
class FetchWindow:
    """The time range a discovery run cares about."""

    since: dt.datetime
    until: dt.datetime


class VoiceSourceAdapter:
    """Base class. Subclasses set ``type`` and implement ``plan``/``fetch``."""

    #: registry ``source.type`` this adapter serves
    type: str = ""
    #: provider name charged against the request budget
    provider: str = ""
    #: registry params a source of this type must supply
    required_params: tuple[str, ...] = ()

    def source_key(self, source) -> str:
        """Stable request-dedupe key for one registered source."""
        raise NotImplementedError

    def plan(self, sources: list, window: FetchWindow) -> list[SourceRequest]:
        """Collapse registered sources into provider requests."""
        raise NotImplementedError

    def fetch(self, request: SourceRequest, http, window: FetchWindow) -> list[Observation]:
        """Execute one planned request. Raises ``AdapterError`` on failure."""
        raise NotImplementedError
