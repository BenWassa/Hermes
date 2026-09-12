"""Remote identity assets for Sports V2.

Only decorative marks from explicitly trusted HTTPS origins may enter the
serialized Sports payload. Team names remain the authoritative identity and
must always render without these assets.
"""

from __future__ import annotations

from urllib.parse import urlparse

TRUSTED_SPORTS_ASSET_HOSTS = frozenset(
    {
        "assets.nhle.com",
        "cdn.nba.com",
        "www.mlbstatic.com",
        "a.espncdn.com",
        "secure.espncdn.com",
    }
)

TORONTO_TEAM_MARKS: dict[str, dict[str, str]] = {
    "leafs": {
        "light": "https://assets.nhle.com/logos/nhl/svg/TOR_light.svg",
        "dark": "https://assets.nhle.com/logos/nhl/svg/TOR_dark.svg",
        "fallback": "ML",
    },
    "raptors": {
        "light": "https://cdn.nba.com/logos/nba/1610612761/primary/L/logo.svg",
        "fallback": "R",
    },
    "blue-jays": {
        "light": "https://www.mlbstatic.com/team-logos/141.svg",
        "fallback": "BJ",
    },
}


def trusted_asset_url(value: object) -> str | None:
    """Return a normalized trusted HTTPS asset URL or ``None``.

    The allowlist deliberately stays narrow. Provider payloads are untrusted
    presentation input even when the underlying sports data is accepted.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = urlparse(value)
    except ValueError:
        return None
    if parsed.scheme != "https" or not parsed.hostname:
        return None
    if parsed.hostname.casefold() not in TRUSTED_SPORTS_ASSET_HOSTS:
        return None
    return value
