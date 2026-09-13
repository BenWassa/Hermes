"""Task 3 - Curate + Summarize (Google Gemini).

One Gemini API call turns the normalized raw-story array into the final
structured edition: dedupe, section, rank, cap, summarize (house voice), and
flag tag + sensitivity.

When deterministic Following seeds are supplied, the same call also writes a
summary for each *already selected* followed article. The model never chooses,
ranks, removes, relinks, or reorders that set; authoritative Voice/article
metadata is joined back after the call and missing model prose degrades to
source metadata rather than dropping the item.

Before the model boundary, deterministic recall protection keeps a small number
of Canada-national and known major-event candidates inside the existing bounded
input. This changes candidate recall, not the one-call model-cost contract.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import time
from collections import defaultdict

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from . import canada, config
from .normalize import curation_view
from .opinion import (
    build_following_cards,
    curation_following_view,
    suppress_opinion_duplicates,
)

log = logging.getLogger("the-daily.curate")

_RETRY_CODES = {429, 500, 503}
_FALLBACK_MODEL = "gemini-2.5-flash"

_FOLLOWING_INSTRUCTION = """

FOLLOWING OVERRIDE FOR THIS REQUEST
The user content is an object with two arrays: `stories` and `following`.

- `stories` is the ordinary editorial pool. Apply all normal dedupe, section,
  ranking, caps, summarization and sensitivity rules to this array only.
- `following` is NOT an editorial candidate pool. Every item has already been
  deterministically selected because the reader explicitly follows its author.
  You have no authority to drop, rank, reorder, substitute, merge, relink or
  move these records into an ordinary section.
- Write prose only from the metadata supplied. Do not invent an argument that
  the headline/description does not support. Summarize the writer's argument as
  their argument, not as the newspaper's own position.
- Return exactly one top-level `following` result for every input Following key.
  Preserve each `key` byte-for-byte. The build will restore all authoritative
  author, publication, image, URL, paywall and identity metadata itself.
- A Following summary should normally be 2 to 3 concise sentences, roughly
  40 to 70 words. `sub` is an optional one-sentence standfirst or null.
- Set `sensitivity` true when the piece is centrally about war, violent crime,
  court proceedings on violent crime, death, or disaster; otherwise false.

For this request the output schema is the ordinary `sections` object plus:
"following": [
  {
    "key": "exact input key",
    "sub": "optional standfirst or null",
    "summary": "faithful concise summary",
    "sensitivity": false
  }
]

Return ONLY the JSON object.
"""


def _client() -> genai.Client:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) not set")
    return genai.Client(api_key=key)


def _gen_config(
    today: dt.date, model: str | None = None, *, include_following: bool = False
) -> types.GenerateContentConfig:
    m = model if model is not None else config.CURATE_MODEL
    system_instruction = config.build_curate_system_prompt(today) + canada.EDITORIAL_INSTRUCTION
    if include_following:
        system_instruction += _FOLLOWING_INSTRUCTION
    kwargs: dict = dict(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        max_output_tokens=config.CURATE_MAX_TOKENS,
        temperature=0.3,
    )
    if "2.5" in m:
        kwargs["thinking_config"] = types.ThinkingConfig(
            thinking_budget=config.CURATE_THINKING_BUDGET
        )
    return types.GenerateContentConfig(**kwargs)


def _generate(
    client: genai.Client,
    contents: str,
    today: dt.date,
    retries: int = 3,
    *,
    include_following: bool = False,
):
    """generate_content with transient backoff and quota-model fallback."""
    models_to_try = [config.CURATE_MODEL]
    if config.CURATE_MODEL != _FALLBACK_MODEL:
        models_to_try.append(_FALLBACK_MODEL)

    last: Exception | None = None
    for model in models_to_try:
        cfg = _gen_config(today, model, include_following=include_following)
        for attempt in range(retries + 1):
            try:
                return client.models.generate_content(
                    model=model, contents=contents, config=cfg
                )
            except genai_errors.APIError as exc:
                code = getattr(exc, "code", None)
                if code in _RETRY_CODES and attempt < retries:
                    wait = min(60, 5 * (2 ** attempt))
                    log.warning("Gemini %s on %s; retrying in %ss", code, model, wait)
                    time.sleep(wait)
                    last = exc
                    continue
                last = exc
                if code == 429 and model != models_to_try[-1]:
                    log.warning(
                        "Quota exhausted on %s; switching to fallback %s",
                        model,
                        models_to_try[-1],
                    )
                break

    raise last  # type: ignore[misc]


def _call(
    client: genai.Client,
    stories: list[dict],
    today: dt.date,
    reinforce: bool = False,
    *,
    following: list[dict] | None = None,
) -> dict:
    editorial = curation_view(stories)
    if following:
        payload: object = {
            "stories": editorial,
            "following": curation_following_view(following),
        }
    else:
        payload = editorial
    user_content = json.dumps(payload, ensure_ascii=False)
    if reinforce:
        user_content = "Return ONLY valid JSON matching the schema.\n\n" + user_content
    resp = _generate(
        client,
        user_content,
        today,
        include_following=bool(following),
    )
    text = resp.text
    if not text:
        reason = resp.candidates[0].finish_reason if resp.candidates else None
        raise RuntimeError(f"Empty curation response (finish_reason={reason})")
    return json.loads(text)


def _story_identity(story: dict) -> str:
    """Exact article identity used only to avoid wasting bounded input slots."""
    canonical = str(story.get("canonical_url") or "").strip()
    if canonical:
        return f"url:{canonical}"
    link = str(story.get("link") or "").strip()
    if link:
        return f"link:{link}"
    return ""


def _dedupe_exact_articles(stories: list[dict]) -> list[dict]:
    """Collapse exact canonical duplicates before bounded input selection."""
    out: list[dict] = []
    seen: set[str] = set()
    for story in stories:
        marker = _story_identity(story)
        if marker and marker in seen:
            continue
        if marker:
            seen.add(marker)
        out.append(story)
    return out


def _round_robin(stories: list[dict], total: int) -> list[dict]:
    """Existing section-hint balancing, kept as the baseline selection rule."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for story in stories:
        buckets[story.get("section_hint", "world")].append(story)

    pools = list(buckets.values())
    out: list[dict] = []
    while len(out) < total and any(pools):
        progressed = False
        for pool in pools:
            if pool:
                out.append(pool.pop(0))
                progressed = True
                if len(out) >= total:
                    break
        if not progressed:
            break
    return out


def _unique_priority(
    stories: list[dict], predicate, limit: int, already: set[int] | None = None
) -> list[dict]:
    """Take a few priority candidates without duplicate canonical identities."""
    if limit <= 0:
        return []
    already = already or set()
    out: list[dict] = []
    seen_markers: set[str] = set()
    for story in stories:
        if id(story) in already or not predicate(story):
            continue
        marker = _story_identity(story)
        if marker and marker in seen_markers:
            continue
        if marker:
            seen_markers.add(marker)
        out.append(story)
        if len(out) >= limit:
            break
    return out


def _trim_input(
    stories: list[dict],
    total: int = config.CURATE_MAX_INPUT,
    *,
    today: dt.date | None = None,
) -> list[dict]:
    """Bound model input while protecting Canada-national and major-event recall.

    Start with the long-standing section-balanced selection. Then ensure a few
    active scheduled-event and Canada-national candidates survive by replacing
    only non-priority tail items. The total input bound never grows and quiet
    days reserve nothing.
    """
    if total <= 0:
        return []
    today = today or dt.date.today()
    unique = _dedupe_exact_articles(stories)
    baseline = _round_robin(unique, min(total, len(unique)))

    event_raw = [story for story in unique if canada.matching_major_event_ids(story, today)]
    canada_raw = [story for story in unique if canada.is_canada_national(story)]

    event_reserved = _unique_priority(
        event_raw,
        lambda _story: True,
        min(canada.MAJOR_EVENT_CURATE_RESERVE, total),
    )
    reserved_ids = {id(story) for story in event_reserved}
    canada_reserved = _unique_priority(
        canada_raw,
        lambda _story: True,
        min(canada.CANADA_CURATE_RESERVE, max(0, total - len(event_reserved))),
        already=reserved_ids,
    )
    reserved = event_reserved + canada_reserved
    reserved_ids.update(id(story) for story in canada_reserved)

    selected = list(baseline)
    selected_ids = {id(story) for story in selected}
    for priority_story in reserved:
        if id(priority_story) in selected_ids:
            continue
        if len(selected) < total:
            selected.append(priority_story)
            selected_ids.add(id(priority_story))
            continue

        victim_index = next(
            (
                index
                for index in range(len(selected) - 1, -1, -1)
                if id(selected[index]) not in reserved_ids
            ),
            None,
        )
        if victim_index is None:
            break
        selected_ids.discard(id(selected[victim_index]))
        selected[victim_index] = priority_story
        selected_ids.add(id(priority_story))

    post_canada = sum(1 for story in selected if canada.is_canada_national(story))
    post_event = sum(
        1 for story in selected if canada.matching_major_event_ids(story, today)
    )
    log.info(
        "curation recall canada=%d/%d major_event=%d/%d selected=%d/%d",
        post_canada,
        len(canada_raw),
        post_event,
        len(event_raw),
        len(selected),
        len(unique),
    )
    return selected


def _normalize_edition(raw: dict) -> list[dict]:
    """Enforce section order, caps, exactly one lead, and lead-only analysis."""
    by_id = {s.get("id"): s for s in raw.get("sections", [])}
    out: list[dict] = []
    for spec in config.SECTIONS:
        section = by_id.get(spec["id"])
        if not section or not section.get("stories"):
            continue
        stories = section["stories"][: spec["cap"]]
        seen_lead = False
        for story in stories:
            if story.get("lead") and not seen_lead:
                seen_lead = True
                story["lead"] = True
            else:
                story["lead"] = False
        if stories and not seen_lead:
            stories[0]["lead"] = True
        for story in stories:
            analysis = (story.get("analysis") or "").strip() if story.get("lead") else ""
            story["analysis"] = analysis or None
        out.append({"id": spec["id"], "label": spec["label"], "stories": stories})
    return out


def _ensure_opinion_section(sections: list[dict]) -> list[dict]:
    """Keep deterministic Following reachable even if editorial Opinion is empty.

    The normal edition omits empty model sections. Once Following exists,
    however, Opinion is also the navigation home of deterministic reader-picked
    work and may no longer disappear because the editorial half happened to
    return zero stories. Insert an empty ordinary Opinion section in canonical
    section order so the renderer can show Following plus a quiet empty
    Today's Opinion state.
    """
    if any(section.get("id") == "opinion" for section in sections):
        return sections

    spec_by_id = {spec["id"]: spec for spec in config.SECTIONS}
    opinion_spec = spec_by_id["opinion"]
    order = {spec["id"]: index for index, spec in enumerate(config.SECTIONS)}
    opinion_rank = order["opinion"]
    insert_at = len(sections)
    for index, section in enumerate(sections):
        if order.get(section.get("id"), len(order)) > opinion_rank:
            insert_at = index
            break
    sections.insert(
        insert_at,
        {"id": "opinion", "label": opinion_spec["label"], "stories": []},
    )
    return sections


def curate(
    stories: list[dict],
    weather: dict | None = None,
    today: dt.date | None = None,
    *,
    following: list[dict] | None = None,
) -> dict:
    """Raw normalized stories -> finished edition, optionally with Following."""
    today = today or dt.date.today()
    client = _client()
    stories = _trim_input(stories, today=today)
    following = list(following or [])
    try:
        raw = _call(client, stories, today, following=following)
    except json.JSONDecodeError:
        log.warning("First curate parse failed; retrying with reinforcement")
        raw = _call(client, stories, today, reinforce=True, following=following)

    sections = _normalize_edition(raw)
    if following:
        _ensure_opinion_section(sections)

    edition = {
        "date": today.strftime("%A, %B %-d, %Y"),
        "weather": weather or {},
        "sections": sections,
    }

    if following:
        edition["following"] = build_following_cards(
            following, raw.get("following"), today=today
        )
        removed = suppress_opinion_duplicates(edition, following)
        if removed:
            log.info(
                "following: suppressed %d duplicate ordinary Opinion card(s) after curation",
                removed,
            )
    return edition


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
    print(
        f"OK: {len(sections)} sections, "
        f"{sum(len(s['stories']) for s in sections)} stories"
    )
    sys.exit(0)
