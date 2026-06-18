"""Task 3 - Curate + Summarize (Google Gemini).

One Gemini API call turns the normalized raw-story array into the final
structured edition: dedupe, section, rank, cap, summarize (house voice), and
flag tag + sensitivity.

Gemini's free tier (Google AI Studio key) comfortably covers one run per day.
`response_mime_type="application/json"` forces valid JSON; the detailed system
prompt carries the exact schema, and a post-pass (exactly one lead per section,
caps) plus a single retry keep the result well formed.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from . import config

log = logging.getLogger("the-daily.curate")

# Transient Gemini errors worth retrying (free tier can briefly 503/429).
_RETRY_CODES = {429, 500, 503}

# If the configured model hits quota exhaustion, fall back to this.
_FALLBACK_MODEL = "gemini-2.5-flash"


def _client() -> genai.Client:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) not set")
    return genai.Client(api_key=key)


def _gen_config(model: str | None = None) -> types.GenerateContentConfig:
    m = model if model is not None else config.CURATE_MODEL
    kwargs: dict = dict(
        system_instruction=config.build_curate_system_prompt(),
        response_mime_type="application/json",
        max_output_tokens=config.CURATE_MAX_TOKENS,
        temperature=0.3,
    )
    # Disable "thinking" on 2.5-series models so the whole output budget goes to
    # the JSON (and the free-tier call stays fast). Older models ignore this.
    if "2.5" in m:
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    return types.GenerateContentConfig(**kwargs)


def _generate(client: genai.Client, contents: str, retries: int = 3):
    """generate_content with backoff on transient errors; falls back to gemini-2.5-flash on quota exhaustion."""
    models_to_try = [config.CURATE_MODEL]
    if config.CURATE_MODEL != _FALLBACK_MODEL:
        models_to_try.append(_FALLBACK_MODEL)

    last: Exception | None = None
    for model in models_to_try:
        cfg = _gen_config(model)
        for attempt in range(retries + 1):
            try:
                return client.models.generate_content(
                    model=model, contents=contents, config=cfg
                )
            except genai_errors.APIError as exc:
                code = getattr(exc, "code", None)
                if code in _RETRY_CODES and attempt < retries:
                    # Use longer waits: Gemini free-tier often needs 30-60s to recover.
                    wait = min(60, 5 * (2 ** attempt))  # 5, 10, 20 … capped at 60s
                    log.warning("Gemini %s on %s; retrying in %ss", code, model, wait)
                    time.sleep(wait)
                    last = exc
                    continue
                last = exc
                if code == 429 and model != models_to_try[-1]:
                    log.warning("Quota exhausted on %s; switching to fallback %s", model, models_to_try[-1])
                break  # move to next model in list

    raise last  # type: ignore[misc]


def _call(client: genai.Client, stories: list[dict], reinforce: bool = False) -> dict:
    user_content = json.dumps(stories, ensure_ascii=False)
    if reinforce:
        user_content = "Return ONLY valid JSON matching the schema.\n\n" + user_content
    resp = _generate(client, user_content)
    text = resp.text
    if not text:
        reason = resp.candidates[0].finish_reason if resp.candidates else None
        raise RuntimeError(f"Empty curation response (finish_reason={reason})")
    return json.loads(text)


def _trim_input(stories: list[dict], total: int = config.CURATE_MAX_INPUT) -> list[dict]:
    """Balance the raw stories across section hints, round-robin, up to `total`.

    Keeps Toronto and each wire section represented rather than letting one
    prolific feed crowd out the rest, and keeps the prompt (and output) small.
    """
    from collections import defaultdict

    buckets: dict[str, list[dict]] = defaultdict(list)
    for s in stories:
        buckets[s.get("section_hint", "world")].append(s)

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


def _normalize_edition(raw: dict) -> list[dict]:
    """Enforce section order, caps, and exactly one lead per section."""
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
        out.append({"id": spec["id"], "label": spec["label"], "stories": stories})
    return out


def curate(stories: list[dict], weather: dict | None = None, today: dt.date | None = None) -> dict:
    """Raw normalized stories -> finished edition dict (date, weather, sections)."""
    client = _client()
    stories = _trim_input(stories)
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
