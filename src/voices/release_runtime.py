"""Runtime bridge from the proven watcher to #26 Hermes release summaries.

The V1 watcher still carries a deprecated ``notify`` field internally.  Rather
than make that field product authority, production narrows the registry to
``tier == core`` first and sets the compatibility bit only on that already-
authoritative set.  Selective and Discovery Voices therefore create no watcher
request, summary, page, or notification pressure.
"""

from __future__ import annotations

from dataclasses import replace

from .notify import Alert, Notifier
from .registry import Registry, TIER_CORE
from .release import PreparedRelease, ReleasePreparer


def core_alert_registry(registry: Registry) -> Registry:
    """Return exactly enabled/disabled Core membership for the release watcher.

    ``notify=True`` below is deliberately a compatibility input to the existing
    claim engine, not a product decision.  The tier filter has already made the
    product decision before it is set.
    """
    return Registry(
        voices=tuple(
            replace(voice, notify=True)
            for voice in registry.voices
            if voice.tier == TIER_CORE
        ),
        version=registry.version,
    )


class ReleaseNotifier(Notifier):
    """Prepare the Hermes page after claim, then delegate the real ntfy send."""

    def __init__(self, *, delegate: Notifier, preparer: ReleasePreparer, registry: Registry):
        self.delegate = delegate
        self.preparer = preparer
        self.registry = registry
        self.prepared: list[PreparedRelease] = []

    def send(self, alert: Alert) -> None:
        article = alert.source_article
        if article is None:
            # Smoke/test notifications are not article releases and should pass
            # through without invoking Gemini or touching article pages.
            self.delegate.send(alert)
            return
        prepared = self.preparer.prepare(
            article,
            self.registry,
            voice_ids=alert.source_voice_ids or tuple(article.voice_ids),
        )
        self.prepared.append(prepared)
        # Propagate NotifyError unchanged.  The watcher will mark the already-
        # durable claim failed and will not retry an ambiguous ntfy attempt.
        self.delegate.send(prepared.alert)
