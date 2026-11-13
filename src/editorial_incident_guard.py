"""High-precision guard against blending two distinct incidents under one link.

Source identity comes only from the actual post-trim editorial input. This is
intentionally narrower than a semantic fact-checker: the observed crash/SIU
failure has two disjoint incident signatures. If the linked article metadata
supports only one, do not attribute the other's generated claim to that link.
Unknown cases abstain rather than guessing or fabricating a second citation.
"""
from __future__ import annotations

import logging
import re

from .editorial_integrity import _unique_exact, _unique_minor_slug_drift

log = logging.getLogger("the-daily.incident-source-guard")

# Narrow, independently observed *incident* categories. Broaden only with
# adjudicated positive AND negative evidence; "police" alone is not a match.
_COLLISION = re.compile(r"\b(?:crash(?:es)?|collis(?:ion|ions)|car accident|vehicle accident)\b", re.I)
_ARREST_FORCE = re.compile(
    r"\b(?:arrest(?:ed|s|ing)?|fare[- ]evasion|police watchdog|"
    r"special investigations unit|SIU|fractured arm during arrest)\b", re.I
)
_SOURCE_FIELDS = ("title", "description")
_CARD_FIELDS = ("headline", "sub", "summary", "analysis")


def _text(record: dict, fields: tuple[str, ...]) -> str:
    return " ".join(str(record.get(key) or "") for key in fields)


def _incident_types(text: str) -> set[str]:
    kinds = set()
    if _COLLISION.search(text):
        kinds.add("collision")
    if _ARREST_FORCE.search(text):
        kinds.add("arrest-force")
    return kinds


def _distinct_event_supported_elsewhere(source: dict, card: dict, pool: list[dict]) -> bool:
    primary_kinds = _incident_types(_text(source, _SOURCE_FIELDS))
    card_kinds = _incident_types(_text(card, _CARD_FIELDS))
    # A collision + arrest can be one coherent event; intervene only when
    # a *different candidate* distinctly explains the otherwise unsupported
    # second type, and the matched source title/description does not.
    if len(primary_kinds) != 1 or not {"collision", "arrest-force"} <= card_kinds:
        return False
    missing_kind = ({"collision", "arrest-force"} - primary_kinds).pop()
    for other in pool:
        if other is source:
            continue
        other_kinds = _incident_types(_text(other, _SOURCE_FIELDS))
        if missing_kind in other_kinds and primary_kinds.isdisjoint(other_kinds):
            return True
    return False


def enforce_incident_source_boundary(sections: list[dict], model_input: list[dict]) -> dict[str, int]:
    """Fail closed to exact same-source public metadata for proven mixed cards.

    Scope: ordinary model-owned cards. Toronto deterministic backfills and
    Following/Sports records are outside this function. Never invent text.
    """
    stats = {"checked": 0, "repaired": 0, "abstained": 0}
    for section in sections:
        for card in section.get("stories", []):
            if card.get("backfill"):
                continue
            link = str(card.get("link") or "")
            source = _unique_exact(link, model_input) or _unique_minor_slug_drift(link, model_input)
            if source is None:
                stats["abstained"] += 1
                continue
            stats["checked"] += 1
            if not _distinct_event_supported_elsewhere(source, card, model_input):
                continue
            title = str(source.get("title") or "").strip()
            if not title:
                stats["abstained"] += 1
                continue
            description = str(source.get("description") or "").strip()
            card["headline"] = title
            card["sub"] = description or None
            card["summary"] = description or title
            card["analysis"] = None
            stats["repaired"] += 1
    if stats["repaired"]:
        log.warning(
            "Cross-incident source boundary: checked=%d repaired=%d abstained=%d",
            stats["checked"], stats["repaired"], stats["abstained"],
        )
    return stats
