"""Release-time alerts over the existing ntfy channel.

Hermes already has one push channel: an ntfy topic that carries the single
"today's edition is ready" message each morning. A followed writer publishing
is the only other thing worth a buzz, so it rides the same channel rather than
introducing a second push stack.

The copy is deliberately flat:

    Jonathan Haidt — After Babel
    Treasure Your Attention

Writer and publication in the title, headline in the body, the publisher's own
canonical URL as the tap target. No BREAKING, no urgency priority, no badge or
unread count, no engagement copy. The morning edition's push is unchanged and
says nothing about individual pieces, so a piece alerted at noon and printed in
tomorrow's paper is announced exactly once either way.

Delivery uses ntfy's JSON publish endpoint rather than the ``X-Title`` header
form the morning workflow uses. Headlines routinely contain em dashes, curly
quotes and accented names, and ntfy's header parsing is ASCII-oriented; a JSON
body is UTF-8 clean. Same service, same topic, same secret.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .. import config
from .model import VoiceArticle
from .urls import url_host

log = logging.getLogger("the-daily.voices.notify")

#: Writers listed by name in one alert before the rest become "& others".
MAX_NAMED_VOICES = 2

DEFAULT_TIMEOUT = 15


class NotifyError(RuntimeError):
    """One alert could not be delivered."""


@dataclass(frozen=True)
class Alert:
    """One release-time notification, ready to send."""

    title: str
    message: str
    click: str
    article_key: str = ""

    def as_payload(self, topic: str) -> dict:
        payload = {
            "topic": topic,
            "title": self.title,
            "message": self.message,
            # ntfy's default priority. Stated rather than omitted so it is
            # clear no urgency escalation is intended, ever.
            "priority": 3,
            "tags": ["memo"],
        }
        if self.click:
            payload["click"] = self.click
        return payload


def voice_names(article: VoiceArticle, registry, *, voice_ids=None) -> str:
    """The writer line: followed names only, in the article's evidence order."""
    ids = list(voice_ids if voice_ids is not None else article.voice_ids)
    names = []
    for voice_id in ids:
        voice = registry.get(voice_id)
        if voice and voice.name not in names:
            names.append(voice.name)
    if not names:
        return ""
    if len(names) <= MAX_NAMED_VOICES:
        return " & ".join(names)
    return f"{' & '.join(names[:MAX_NAMED_VOICES])} & others"


def build_alert(article: VoiceArticle, registry, *, voice_ids=None) -> Alert:
    """Compose the alert for one newly discovered article.

    A co-authored piece by two followed writers is one alert naming both, not
    one alert per writer: the reader gained one article to read.
    """
    writers = voice_names(article, registry, voice_ids=voice_ids)
    publication = article.publication or url_host(article.canonical_url or article.url)
    title = " — ".join(part for part in (writers, publication) if part)
    # The tap target is the publisher's own URL as the source stated it, not
    # the canonical form. Canonicalisation exists to compare and to key on:
    # it drops "www." and other addressing detail that some hosts still need.
    link = article.url or article.canonical_url
    return Alert(
        title=title or "A followed writer",
        message=article.title or link,
        click=link,
        article_key=article.key,
    )


class Notifier:
    """Delivery contract. ``send`` raises ``NotifyError`` and nothing else."""

    def send(self, alert: Alert) -> None:
        raise NotImplementedError


class NtfyNotifier(Notifier):
    """Publishes to an ntfy topic."""

    def __init__(self, topic: str, *, base_url: str | None = None, session=None,
                 timeout: int = DEFAULT_TIMEOUT):
        if not topic:
            raise ValueError("ntfy topic is required")
        self.topic = topic
        self.base_url = (base_url or config.NTFY_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._session = session

    def _post(self, payload: dict):
        session = self._session
        if session is None:
            import requests

            session = requests.Session()
            self._session = session
        return session.post(self.base_url + "/", json=payload, timeout=self.timeout)

    def send(self, alert: Alert) -> None:
        try:
            response = self._post(alert.as_payload(self.topic))
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001 - every failure is one failed alert
            raise NotifyError(f"ntfy publish failed: {exc}") from exc
        log.info("voice watch: alerted %r / %r", alert.title, alert.message)


class RecordingNotifier(Notifier):
    """Records alerts without sending them. Used by ``--dry-run`` and tests."""

    def __init__(self):
        self.sent: list[Alert] = []

    def send(self, alert: Alert) -> None:
        self.sent.append(alert)
        log.info("voice watch (dry run): would alert %r / %r", alert.title, alert.message)
