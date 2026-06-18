"""Task 3 - Curate + Summarize.

One Anthropic Messages API call turns the normalized raw-story array into the
final structured edition: dedupe, section, rank, cap, summarize (house voice),
and flag tag + sensitivity.

Uses structured outputs (`output_config.format` with a JSON schema) so the
response is guaranteed to be schema-valid JSON, which removes most of the JSON
drift risk. A light retry plus a post-pass (exactly one lead per section, caps)
keeps the result well formed even if the model returns something off-spec.
"""

from __future__ import annotations

import datetime as dt
import json
import logging

import anthropic

from . import config

log = logging.getLogger("the-daily.curate")


# JSON schema the model must return. Only the `sections` array; `date` and
# `weather` are injected locally afterwards.
_STORY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string"},
        "lead": {"type": "boolean"},
        "kicker": {"type": "string"},
        "headline": {"type": "string"},
        "sub": {"type": "string"},
        "summary": {"type": "string"},
        "time": {"type": "string"},
        "tag": {"type": ["string", "null"]},
        "sensitivity": {"type": "boolean"},
        "image": {"type": ["string", "null"]},
        "link": {"type": "string"},
    },
    "required": [
        "id", "lead", "kicker", "headline", "sub", "summary",
        "time", "tag", "sensitivity", "image", "link",
    ],
}

EDITION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "stories": {"type": "array", "items": _STORY_SCHEMA},
                },
                "required": ["id", "label", "stories"],
            },
        }
    },
    "required": ["sections"],
}


def _call(client: anthropic.Anthropic, stories: list[dict], reinforce: bool = False) -> dict:
    """One structured Messages API call; returns parsed JSON."""
    user_content = json.dumps(stories, ensure_ascii=False)
    if reinforce:
        user_content = "Return ONLY valid JSON matching the schema.\n\n" + user_content
    resp = client.messages.create(
        model=config.CURATE_MODEL,
        max_tokens=config.CURATE_MAX_TOKENS,
        system=config.build_curate_system_prompt(),
        messages=[{"role": "user", "content": user_content}],
        output_config={"format": {"type": "json_schema", "schema": EDITION_SCHEMA}},
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"Curation refused: {resp.stop_details}")
    if resp.stop_reason == "max_tokens":
        log.warning("Curation hit max_tokens; output may be truncated")
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return json.loads(text)


def _normalize_edition(raw: dict) -> list[dict]:
    """Enforce section order, caps, and exactly one lead per section."""
    by_id = {s.get("id"): s for s in raw.get("sections", [])}
    out: list[dict] = []
    for spec in config.SECTIONS:
        section = by_id.get(spec["id"])
        if not section or not section.get("stories"):
            continue
        stories = section["stories"][: spec["cap"]]
        # Exactly one lead: keep the first flagged, else promote the first story.
        seen_lead = False
        for story in stories:
            if story.get("lead") and not seen_lead:
                seen_lead = True
                story["lead"] = True
            else:
                story["lead"] = False
        if stories and not seen_lead:
            stories[0]["lead"] = True
        out.append({"id": spec["id"], "label": spec["label"], "stories": stories})
    return out


def curate(stories: list[dict], weather: dict | None = None, today: dt.date | None = None) -> dict:
    """Raw normalized stories -> finished edition dict (date, weather, sections)."""
    client = anthropic.Anthropic()
    try:
        raw = _call(client, stories)
    except json.JSONDecodeError:
        log.warning("First curate parse failed; retrying with reinforcement")
        raw = _call(client, stories, reinforce=True)

    today = today or dt.date.today()
    return {
        "date": today.strftime("%A, %B %-d, %Y"),
        "weather": weather or {},
        "sections": _normalize_edition(raw),
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    fixture = Path("data/fixtures/normalized_sample.json")
    if fixture.exists():
        stories = json.loads(fixture.read_text())
    else:
        from .fetch import fetch_all
        from .normalize import normalize

        stories = normalize(fetch_all())

    edition = curate(stories)

    # Schema-ish validation for the test gate.
    sections = edition["sections"]
    assert 5 <= len(sections) <= 6, f"expected 5-6 sections, got {len(sections)}"
    for s in sections:
        leads = [st for st in s["stories"] if st["lead"]]
        assert s["stories"], f"{s['id']} has no stories"
        assert len(leads) == 1, f"{s['id']} has {len(leads)} leads"
        for st in s["stories"]:
            assert st["summary"].strip(), f"{st['id']} empty summary"
            assert isinstance(st["sensitivity"], bool)

    Path("data/fixtures/edition_sample.json").write_text(
        json.dumps(edition, indent=2, ensure_ascii=False)
    )
    print(f"OK: {len(sections)} sections, "
          f"{sum(len(s['stories']) for s in sections)} stories")
    sys.exit(0)
