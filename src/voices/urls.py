"""Canonical URL normalization and article identity keys.

Two related jobs:

* ``canonical_url`` produces a comparable form of an article URL by removing
  the noise that varies between discovery paths (tracking parameters, AMP
  mirrors, host prefixes, trailing slashes) while leaving anything that could
  distinguish two genuinely different articles alone.
* ``identity_keys`` produces the set of keys an observation may be merged on.
  Two observations are the same article when they share *any* key.

Both are deliberately conservative. Over-normalizing silently merges distinct
articles, which is worse than showing a duplicate.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Query parameters that never identify an article. Prefix rules cover the
# open-ended analytics families; exact names cover the rest.
_TRACKING_PREFIXES = ("utm_", "at_", "mc_", "pk_", "piwik_", "hsa_", "vero_", "_hs")
_TRACKING_EXACT = {
    "cmp", "cmpid", "campaign_id", "fbclid", "gclid", "dclid", "msclkid",
    "igshid", "ito", "ns_campaign", "ns_mchannel", "ns_source", "ncid",
    "ref", "ref_src", "referrer", "referring_source", "source", "src",
    "smid", "smtyp", "partner", "sh", "share", "shareid", "sharetype",
    "__twitter_impression", "spm", "yclid", "wtmc", "xtor", "guccounter",
    "guce_referrer", "guce_referrer_sig", "triedsignin", "amp",
    "publication_id", "post_id", "isfreemail", "r", "showwelcome",
}

# Host prefixes that address the same site.
_HOST_PREFIXES = ("www.", "m.", "amp.", "mobile.")

_AMP_PATH_RE = re.compile(r"/amp(?:/|$)|\.amp(?:/|$)|/amp\.html$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def normalize_host(host: str) -> str:
    """Lowercase a host and drop an addressing prefix such as ``www.``."""
    host = (host or "").lower().strip().rstrip(".")
    if host.startswith("["):  # IPv6 literal, leave alone
        return host
    for prefix in _HOST_PREFIXES:
        if host.startswith(prefix) and host.count(".") >= 2:
            return host[len(prefix):]
    return host


def _is_tracking(param: str) -> bool:
    name = param.lower()
    return name in _TRACKING_EXACT or name.startswith(_TRACKING_PREFIXES)


def canonical_url(url: str | None) -> str:
    """A comparable canonical form of an article URL.

    Returns "" for anything that is not an absolute http(s) URL. The original
    URL is never replaced by this value in output records; it exists purely to
    compare and to key on.
    """
    if not url or not isinstance(url, str):
        return ""
    raw = url.strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
    except ValueError:
        return ""
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        return ""

    host = normalize_host(parts.hostname or "")
    if not host:
        return ""
    # Keep a non-default port; it genuinely addresses a different service.
    port = parts.port
    if port and port not in (80, 443):
        host = f"{host}:{port}"

    path = re.sub(r"/{2,}", "/", parts.path or "/")
    path = _AMP_PATH_RE.sub("/", path)
    if len(path) > 1:
        path = path.rstrip("/") or "/"

    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _is_tracking(k)]
    query = urlencode(sorted(kept), doseq=True)

    # Fragments are presentational for news articles. A hashbang is not, so it
    # is preserved.
    fragment = parts.fragment if parts.fragment.startswith("!") else ""

    return urlunsplit(("https", host, path, query, fragment))


def url_host(url: str | None) -> str:
    """Normalized host of a URL, or "" when it has none."""
    canonical = canonical_url(url)
    if not canonical:
        return ""
    return urlsplit(canonical).hostname or ""


def title_slug(title: str | None, limit: int = 12) -> str:
    """A bounded, comparable slug of an article title."""
    if not title:
        return ""
    folded = unicodedata.normalize("NFKD", str(title))
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch)).lower()
    words = [w for w in _SLUG_RE.split(folded) if w]
    return "-".join(words[:limit])


def provider_key(provider: str, article_id: str | None) -> str:
    """Identity key for a provider-native article id."""
    if not provider or not article_id:
        return ""
    return f"pid:{provider.strip().lower()}:{str(article_id).strip()}"


def url_key(url: str | None) -> str:
    """Identity key for a URL."""
    canonical = canonical_url(url)
    return f"url:{canonical}" if canonical else ""


def fingerprint_key(url: str | None, title: str | None, day: str | None) -> str:
    """Same-host fallback identity key.

    Only ever merges observations from the *same* host published on the same
    day with the same normalized title, so it cannot collapse two publishers'
    versions of a story. Requires all three components.
    """
    host, slug = url_host(url), title_slug(title)
    if not host or not slug or not day:
        return ""
    return f"fp:{host}|{slug}|{day}"


def syndication_key(title: str | None, author_key: str | None, day: str | None) -> str:
    """Cross-publisher grouping key for the same piece run in two places.

    Deliberately *not* an identity key: syndicated copies stay distinct
    articles with their own canonical URLs, they are only grouped so that
    Following shows (and later notifies about) one of them. Requires an
    author, so two unrelated articles that happen to share a title never
    group.
    """
    slug = title_slug(title)
    if not slug or not author_key or not day:
        return ""
    return f"syn:{slug}|{author_key}|{day}"
