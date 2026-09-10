from __future__ import annotations

import datetime as dt
import json
from types import SimpleNamespace

from src.voice_digest import (
    DeterministicWeeklyCurator,
    GeminiWeeklyCurator,
    WEEKLY_CAP,
    WeeklyCuration,
    WeeklyCurator,
    build_weekly_alert,
    publish_weekly_screened,
    recent_items,
    render_recent,
    render_weekly,
)
from src.voices.notify import RecordingNotifier
from src.voices.registry import Registry, TIER_CORE, TIER_DISCOVERY, Voice
from src.voices.roundup import period_for_id
from src.voices.roundup_state import FileRoundupStore, RoundupState

UTC = dt.timezone.utc
PERIOD = period_for_id("2026-09-13")
NOW = PERIOD.cutoff + dt.timedelta(minutes=43)


def registry() -> Registry:
    return Registry(
        voices=(
            Voice(id="a", name="Alpha Writer", tier=TIER_CORE),
            Voice(id="b", name="Beta Writer", tier=TIER_CORE),
            Voice(id="c", name="Gamma Writer", tier=TIER_CORE),
            Voice(id="d", name="Delta Writer", tier=TIER_CORE),
            Voice(id="discovery", name="Discovery Writer", tier=TIER_DISCOVERY),
        )
    )


def state_with_items() -> RoundupState:
    state = RoundupState(collecting_since=PERIOD.start - dt.timedelta(hours=1))
    for index, voice in enumerate(("a", "b", "c", "d"), start=1):
        published = PERIOD.cutoff - dt.timedelta(hours=index)
        link = f"https://example.com/{voice}"
        state.observe(
            key=f"url:{link}",
            keys={f"url:{link}"},
            voice_ids=(voice,),
            first_seen=published + dt.timedelta(minutes=5),
            published_at=published,
            title=f"Substantive essay {voice.upper()}",
            url=link,
            publication="Example Review",
            first_morning_surfaced_at=None,
        )
    return state


class FixedCurator(WeeklyCurator):
    def __init__(self):
        self.calls = 0

    def curate(self, candidates, registry, *, period):
        self.calls += 1
        keys = tuple(item.key for item in candidates[:2])
        return WeeklyCuration(
            selected_keys=keys,
            summary="Two pieces look most worth limited attention this week.",
            reasons={keys[0]: "Most likely to add a new explanatory frame."},
            model_used=True,
        )


def test_deterministic_fallback_is_deliberately_small_and_one_per_voice():
    reg = registry()
    state = state_with_items()
    candidates = list(state.items.values())

    result = DeterministicWeeklyCurator().curate(candidates, reg, period=PERIOD)

    assert 1 <= len(result.selected_keys) <= WEEKLY_CAP == 3
    selected = [state.items[key] for key in result.selected_keys]
    assert len({item.voice_ids[0] for item in selected}) == len(selected)
    assert not result.model_used


def test_gemini_screen_is_one_call_and_rejects_non_candidate_keys():
    reg = registry()
    state = state_with_items()
    candidates = list(state.items.values())
    valid = candidates[0].key

    class Models:
        def __init__(self):
            self.calls = 0

        def generate_content(self, **kwargs):
            self.calls += 1
            return SimpleNamespace(
                text=json.dumps(
                    {
                        "selected_keys": [valid, "url:https://evil.invalid/not-a-candidate"],
                        "summary": "A small shortlist, chosen for likely explanatory value rather than publication frequency.",
                        "reasons": {valid: "The headline signals a substantive explanatory question."},
                    }
                )
            )

    models = Models()
    client = SimpleNamespace(models=models)
    result = GeminiWeeklyCurator(client=client, model="gemini-test").curate(
        candidates, reg, period=PERIOD
    )

    assert models.calls == 1
    assert result.selected_keys == (valid,)
    assert result.model_used


def test_weekly_claim_publishes_then_notifies_once_across_rerun(tmp_path, monkeypatch):
    reg = registry()
    state = state_with_items()
    state_path = tmp_path / "state.json"
    page_path = tmp_path / "voices" / "index.html"
    state_path.write_text(state.dumps(), encoding="utf-8")
    store = FileRoundupStore(state_path)
    notifier = RecordingNotifier()
    curator = FixedCurator()
    monkeypatch.setattr("src.voices.roundup_settings.PAGE_PATH", page_path)
    monkeypatch.setattr("src.config.SITE_URL", "https://example.test/Hermes/")

    first = publish_weekly_screened(
        reg,
        store=store,
        notifier=notifier,
        now=NOW,
        period=PERIOD,
        curator=curator,
        refresh=False,
    )
    second = publish_weekly_screened(
        reg,
        store=store,
        notifier=notifier,
        now=NOW + dt.timedelta(minutes=10),
        period=PERIOD,
        curator=curator,
        refresh=False,
    )

    assert first == 0 and second == 0
    assert curator.calls == 1
    assert len(notifier.sent) == 1
    assert notifier.sent[0].click == "https://example.test/Hermes/voices/"
    assert "one weekly Voices brief" in notifier.sent[0].message
    page = page_path.read_text(encoding="utf-8")
    assert "A small weekly reading brief." in page
    assert "Worth your time" in page
    assert "Browse all recent Core writing" in page


def test_recent_shelf_is_finite_quiet_and_has_no_notification_language_pressure():
    reg = registry()
    state = state_with_items()
    items = recent_items(state, reg, cap=2)
    page = render_recent(state, reg)

    assert len(items) == 2
    assert "Quiet shelf" in page
    assert "Nothing on this page creates a notification or unread obligation." in page
    assert "Unread" not in page
    assert "Load more" not in page


def test_weekly_page_is_one_summary_plus_at_most_three_selected_items():
    reg = registry()
    state = state_with_items()
    selected = list(state.items.values())[:3]
    curation = WeeklyCuration(
        selected_keys=tuple(item.key for item in selected),
        summary="This is the single weekly editorial summary.",
        reasons={},
        model_used=True,
    )
    page = render_weekly(PERIOD, selected, reg, curation)

    assert page.count('class="piece"') == 3
    assert page.count("This is the single weekly editorial summary.") == 1
    assert "article-by-article alerts" in page


def test_weekly_alert_is_one_compact_pointer(monkeypatch):
    reg = registry()
    state = state_with_items()
    selected = list(state.items.values())[:2]
    monkeypatch.setattr("src.config.SITE_URL", "https://example.test/Hermes/")

    alert = build_weekly_alert(selected, reg)
    payload = alert.as_payload("topic")

    assert alert.title == "Voices this week"
    assert alert.click == "https://example.test/Hermes/voices/"
    assert "one weekly Voices brief" in alert.message
    assert payload["priority"] == 3
