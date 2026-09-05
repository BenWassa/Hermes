"""Adapter registry.

Adapters are looked up by the registry ``source.type``. Adding a source type
means adding a module here and nothing else: the registry validator, the
discovery planner, and the resolver all read this table.
"""

from __future__ import annotations

from .author_page import AuthorPageAdapter
from .base import AdapterError, FetchWindow, SourceRequest, VoiceSourceAdapter
from .guardian import GuardianContributorAdapter
from .perigon import PerigonJournalistAdapter
from .rss import RssAdapter

ADAPTERS: dict[str, VoiceSourceAdapter] = {
    adapter.type: adapter
    for adapter in (
        RssAdapter(),
        GuardianContributorAdapter(),
        PerigonJournalistAdapter(),
        AuthorPageAdapter(),
    )
}

ADAPTER_TYPES = frozenset(ADAPTERS)


def get_adapter(source_type: str) -> VoiceSourceAdapter:
    try:
        return ADAPTERS[source_type]
    except KeyError as exc:
        raise AdapterError(f"unknown voice source type '{source_type}'") from exc


def required_params(source_type: str) -> tuple[str, ...]:
    adapter = ADAPTERS.get(source_type)
    return adapter.required_params if adapter else ()


def source_key_for(source) -> str:
    """The request-dedupe key for a registered source."""
    adapter = ADAPTERS.get(source.type)
    if adapter is None:
        return f"{source.type}:{source.id}"
    return adapter.source_key(source)


__all__ = [
    "ADAPTERS",
    "ADAPTER_TYPES",
    "AdapterError",
    "FetchWindow",
    "SourceRequest",
    "VoiceSourceAdapter",
    "get_adapter",
    "required_params",
    "source_key_for",
]
