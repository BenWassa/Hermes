"""Release-time alerts over the existing ntfy channel.

The watcher creates an :class:`Alert` only after an article claim is durable.
For Core release alerts that object may also carry the in-memory canonical
article and Voice ids to the release-summary notifier.  Those fields are never
serialized to ntfy or durable watcher state; they simply preserve the safe
claim-before-send ordering while allowing #26 to prepare a Hermes destination
before the actual push.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

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
    """One release-time notification, ready to send.

    ``source_article`` and ``source_voice_ids`` are process-local preparation
    context.  They deliberately do not appear in :meth:`as_payload` and are
    not written to watcher state.
    """

    title: str
    message: str
    click: str
    article_key: str = ""
    source_article: VoiceArticle | None = field(default=None, repr=False, compare=False)
    source_voice_ids: tuple[str, ...] = field(default=(), repr=False, compare=False)

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
    """Compose the post-claim candidate alert for one canonical article.

    The direct publisher URL remains a safe fallback.  The #26 release notifier
    replaces the visible copy and tap target with the stable Hermes summary
    page when that page can be prepared successfully.
    """
    ids = tuple(voice_ids if voice_ids is not None else article.voice_ids)
    writers = voice_names(article, registry, voice_ids=ids)
    publication = article.publication or url_host(article.canonical_url or article.url)
    title = " — ".join(part for part in (writers, publication) if part)
    link = article.url or article.canonical_url
    return Alert(
        title=title or "A followed writer",
        message=article.title or link,
        click=link,
        article_key=article.key,
        source_article=article,
        source_voice_ids=ids,
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
