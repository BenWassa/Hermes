from __future__ import annotations

import datetime as dt
import json
from types import SimpleNamespace

from src.voice_weekly import GroundedGeminiWeeklyCurator
from src.voices.registry import Registry, TIER_CORE, Voice
from src.voices.roundup import period_for_id
from src.voices.roundup_state import RoundupState
from src.voices.weekly_context import description_for_item

PERIOD = period_for_id("2026-09-13")


def registry() -> Registry:
    return Registry(voices=(Voice(id="a", name="Alpha Writer", tier=TIER_CORE),))


def one_item():
    state = RoundupState(collecting_since=PERIOD.start - dt.timedelta(hours=1))
    link = "https://example.com/alpha"
    item, _ = state.observe(
        key=f"url:{link}",
        keys={f"url:{link}", "pid:alpha-1"},
        voice_ids=("a",),
        first_seen=PERIOD.cutoff - dt.timedelta(hours=3),
        published_at=PERIOD.cutoff - dt.timedelta(hours=4),
        title="Why productivity is diverging across rich economies",
        url=link,
        publication="Example Review",
    )
    return item


def test_description_for_item_matches_any_retained_identity_key():
    item = one_item()
    descriptions = {
        "pid:alpha-1": "A public feed excerpt explaining that diffusion of AI tools differs sharply by firm size."
    }

    assert "diffusion of AI tools" in description_for_item(item, descriptions)


def test_grounded_curator_uses_public_excerpt_and_only_one_model_call():
    reg = registry()
    item = one_item()
    loader_calls = []
    captured = []

    def context_loader(registry, period):
        loader_calls.append((registry, period))
        return {
            "pid:alpha-1": (
                "A public publisher-feed excerpt says productivity gains are concentrated in "
                "large firms adopting AI-assisted workflows, while smaller firms lag."
            )
        }

    class Models:
        def generate_content(self, **kwargs):
            captured.append(kwargs)
            return SimpleNamespace(
                text=json.dumps(
                    {
                        "selected_keys": [item.key],
                        "summary": "One piece is worth attention because its public excerpt points to a concrete productivity-diffusion question.",
                        "reasons": {
                            item.key: "The supplied excerpt identifies a consequential adoption gap rather than a routine reaction."
                        },
                    }
                )
            )

    curator = GroundedGeminiWeeklyCurator(
        client=SimpleNamespace(models=Models()),
        model="gemini-test",
        context_loader=context_loader,
    )
    result = curator.curate([item], reg, period=PERIOD)

    assert len(loader_calls) == 1
    assert len(captured) == 1
    payload = json.loads(captured[0]["contents"])
    candidate = payload["candidates"][0]
    assert "productivity gains are concentrated" in candidate["source_description"]
    assert "public feed/archive excerpt" in payload["evidence_boundary"]
    assert result.selected_keys == (item.key,)
    assert result.model_used is True


def test_grounded_curator_continues_conservatively_when_context_pass_fails():
    reg = registry()
    item = one_item()
    captured = []

    def broken_loader(registry, period):
        raise RuntimeError("publisher feed temporarily unavailable")

    class Models:
        def generate_content(self, **kwargs):
            captured.append(json.loads(kwargs["contents"]))
            return SimpleNamespace(
                text=json.dumps(
                    {
                        "selected_keys": [item.key],
                        "summary": "Metadata-only screening kept this candidate, with the evidence limitation explicit.",
                        "reasons": {item.key: "Potentially substantive from the headline, but evidence is limited."},
                    }
                )
            )

    curator = GroundedGeminiWeeklyCurator(
        client=SimpleNamespace(models=Models()),
        model="gemini-test",
        context_loader=broken_loader,
    )
    result = curator.curate([item], reg, period=PERIOD)

    assert len(captured) == 1
    assert captured[0]["candidates"][0]["source_description"] is None
    assert result.selected_keys == (item.key,)
