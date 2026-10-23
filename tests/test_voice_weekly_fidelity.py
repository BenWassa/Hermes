"""Issue #70: weekly Voices roundup editorial fidelity.

Everything here is deterministic: the single weekly model call is faked, and the
assertions cover what Hermes does with its (untrusted) output.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from types import SimpleNamespace

import pytest

from src.voice_digest import (
    WEEKLY_CAP,
    WEEKLY_MAX_PER_VOICE,
    GeminiWeeklyCurator,
    WeeklyCuration,
    WeeklyCurator,
    finalize_curation,
    publish_weekly_screened,
    render_weekly,
)
from src.voice_weekly import GroundedGeminiWeeklyCurator
from src.voices import weekly_fidelity as fid
from src.voices.notify import RecordingNotifier
from src.voices.registry import TIER_CORE, Registry, Voice
from src.voices.roundup import period_for_id
from src.voices.roundup_state import FileRoundupStore, RoundupState

PERIOD = period_for_id("2026-09-13")
NOW = PERIOD.cutoff + dt.timedelta(minutes=43)

TITLES = {
    "a": "Why the recursive self-improvement race cannot be regulated away",
    "b": "Does the internet make people less religious?",
    "c": "A very different essay on Canadian federalism",
    "d": "Notes on the Italian landscape and its cities",
}


def registry() -> Registry:
    return Registry(
        voices=(
            Voice(id="a", name="Alpha Writer", tier=TIER_CORE),
            Voice(id="b", name="Beta Writer", tier=TIER_CORE),
            Voice(id="c", name="Gamma Writer", tier=TIER_CORE),
            Voice(id="d", name="Delta Writer", tier=TIER_CORE),
        )
    )


def make_state(voices=("a", "b", "c", "d")) -> RoundupState:
    state = RoundupState(collecting_since=PERIOD.start - dt.timedelta(hours=1))
    for index, voice in enumerate(voices, start=1):
        published = PERIOD.cutoff - dt.timedelta(hours=index)
        link = f"https://example.com/{voice}/{index}"
        state.observe(
            key=f"url:{link}",
            keys={f"url:{link}"},
            voice_ids=(voice,),
            first_seen=published + dt.timedelta(minutes=5),
            published_at=published,
            title=TITLES[voice] if voices.count(voice) == 1 else f"{TITLES[voice]} part {index}",
            url=link,
            publication=f"Pub {voice.upper()}",
        )
    return state


def by_voice(state: RoundupState) -> dict[str, object]:
    return {item.voice_ids[0]: item for item in state.items.values()}


class FakeModels:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text=json.dumps(self.payload))


def gemini(payload: dict) -> tuple[GeminiWeeklyCurator, FakeModels]:
    models = FakeModels(payload)
    return GeminiWeeklyCurator(client=SimpleNamespace(models=models), model="gemini-test"), models


def run_publish(tmp_path, monkeypatch, state, curator, *, store=None):
    state_path = tmp_path / "state.json"
    state_path.write_text(state.dumps(), encoding="utf-8")
    page_path = tmp_path / "voices" / "index.html"
    monkeypatch.setattr("src.voices.roundup_settings.PAGE_PATH", page_path)
    monkeypatch.setattr("src.config.SITE_URL", "https://example.test/Hermes/")
    store = store or FileRoundupStore(state_path)
    notifier = RecordingNotifier()
    code = publish_weekly_screened(
        registry(), store=store, notifier=notifier, now=NOW, period=PERIOD,
        curator=curator, refresh=False,
    )
    page = page_path.read_text(encoding="utf-8") if page_path.exists() else ""
    return code, page, notifier, FileRoundupStore(state_path).load()


def rendered_titles(page: str) -> list[str]:
    import html as html_mod

    return [html_mod.unescape(t) for t in re.findall(r"<h2>(.*?)</h2>", page)]


GOOD_SUMMARY = (
    "Alpha Writer argues that rivals cannot slow recursive self-improvement unilaterally, "
    "while Beta Writer reports that internet use is associated with lower religious attendance."
)


# --- canonical metadata is authoritative -------------------------------------------------


def test_model_cannot_replace_canonical_titles_in_cards_or_prose(tmp_path, monkeypatch):
    state = make_state()
    items = by_voice(state)
    keys = [items["a"].key, items["b"].key]
    curator, _ = gemini(
        {
            "selected_keys": keys,
            # Ignored model-supplied title/author fields, plus a reworded quoted headline.
            "titles": {keys[0]: "AI self-regulation is coming"},
            "headline": "AI self-regulation",
            "summary": (
                "Alpha Writer's “AI self-regulation and the future” meets Beta Writer's piece."
            ),
            "summary_covers": keys,
            "reasons": {keys[0]: "Argues that self-improving systems outpace oversight."},
        }
    )
    code, page, _, _ = run_publish(tmp_path, monkeypatch, state, curator)

    assert code == 0
    assert set(rendered_titles(page)) == {items["a"].title, items["b"].title}
    assert "AI self-regulation" not in page
    # The reworded quote is replaced by a canonical, metadata-only lead.
    assert f"“{items['a'].title}”" in page
    # Attribution, publication, date and URL survive unchanged.
    assert "Alpha Writer" in page and "Pub A" in page and items["a"].url in page
    assert "Sep 13" in page


def test_quoted_title_must_be_exact_canonical_substring():
    piece = fid.Piece("k", "China fact (?) of the day", ("Alpha Writer",), "Pub")
    other = fid.Piece("o", "Unselected essay about wheat", ("Beta Writer",), "Pub")
    assert fid.quoted_title_problems("A “China fact of the day” note.", [piece], [piece])
    assert not fid.quoted_title_problems("A “China fact (?) of the day” note.", [piece], [piece])
    assert fid.quoted_title_problems("See “Unselected essay about wheat” too.", [piece], [piece, other])
    # Short scare-quotes are not title references.
    assert not fid.quoted_title_problems('The "global south" framing.', [piece], [piece])


def test_missing_voice_attribution_or_url_is_excluded_not_rendered(tmp_path, monkeypatch):
    state = make_state(("a", "b", "c"))
    orphan_link = "https://example.com/orphan"
    orphan, _ = state.observe(
        key=f"url:{orphan_link}", keys={f"url:{orphan_link}"}, voice_ids=("unknown-voice",),
        first_seen=NOW, published_at=PERIOD.cutoff - dt.timedelta(hours=1),
        title="Orphan piece with no Core attribution", url=orphan_link, publication="Pub X",
    )
    items = by_voice(state)
    keys = [orphan.key, items["a"].key]
    curation = WeeklyCuration(
        tuple(keys), GOOD_SUMMARY, {}, True, covers=tuple(keys),
    )
    selected, final = finalize_curation(
        curation, dict(state.items), list(state.items.values()), registry()
    )

    assert [item.key for item in selected] == [items["a"].key]
    assert any("missing Core Voice attribution" in issue for issue in final.issues)
    # The two-piece synthesis is not reused for the one-piece set.
    assert final.summary != GOOD_SUMMARY
    assert final.summary == fid.canonical_summary(
        [fid.Piece(items["a"].key, items["a"].title, ("Alpha Writer",), "Pub A")]
    )


def test_unresolvable_selection_yields_empty_status_and_no_notification(tmp_path, monkeypatch):
    state = make_state(("a",))

    class Ghost(WeeklyCurator):
        def curate(self, candidates, registry, *, period):
            return WeeklyCuration(("url:https://nowhere.invalid/x",), "Ghost summary.", {}, True)

    code, page, notifier, saved = run_publish(tmp_path, monkeypatch, state, Ghost())

    assert code == 0
    assert notifier.sent == []
    assert saved.last_roundup.status == "empty"
    assert 'class="piece"' not in page and "Ghost summary" not in page


# --- selected set vs synthesis vs rendered cards -----------------------------------------


@pytest.mark.parametrize("n", [1, 2, 3])
def test_rendered_cards_claim_and_alert_match_final_selection(tmp_path, monkeypatch, n):
    state = make_state()
    items = by_voice(state)
    keys = [items[v].key for v in ("a", "b", "c")[:n]]
    curator, _ = gemini({"selected_keys": keys, "summary": "Alpha Writer and Beta Writer make separate arguments.", "summary_covers": keys[:2]})
    code, page, notifier, saved = run_publish(tmp_path, monkeypatch, state, curator)

    assert code == 0
    assert page.count('class="piece"') == n
    assert saved.last_roundup.selection_keys == tuple(keys)
    assert f"Worth your time · {n} piece" in page
    assert len(notifier.sent) == 1
    assert "Delta Writer" not in notifier.sent[0].message


def test_summary_discussing_three_pieces_when_one_is_selected_is_replaced(tmp_path, monkeypatch):
    """The Sept 20 failure: a three-piece synthesis above a single visible card."""
    state = make_state()
    items = by_voice(state)
    only = items["a"].key
    curator, _ = gemini(
        {
            "selected_keys": [only],
            "summary": "Three pieces this week connect AI, religion and federalism through one shared worry.",
            "summary_covers": [only],
        }
    )
    _, page, _, _ = run_publish(tmp_path, monkeypatch, state, curator)

    assert page.count('class="piece"') == 1
    assert "Three pieces" not in page and "shared worry" not in page
    assert f"“{items['a'].title}”" in page


def test_summary_naming_unselected_piece_or_writer_is_replaced():
    state = make_state()
    items = by_voice(state)
    pool = list(state.items.values())
    reg = registry()
    base = WeeklyCuration((items["a"].key,), "", {}, True)

    for text in (
        f"Alpha Writer is joined by {items['b'].title.lower()} as a counterpoint.",
        "Alpha Writer's argument contrasts with Gamma Writer's federalism essay.",
    ):
        selected, final = finalize_curation(
            WeeklyCuration(base.selected_keys, text, {}, True), dict(state.items), pool, reg
        )
        assert [i.key for i in selected] == [items["a"].key]
        assert final.summary != text and final.issues


def test_summary_covers_must_be_subset_of_selected():
    state = make_state()
    items = by_voice(state)
    pool = list(state.items.values())
    curation = WeeklyCuration(
        (items["a"].key,), "Alpha Writer argues the race cannot be paused.", {}, True,
        covers=(items["a"].key, items["b"].key),
    )
    _, final = finalize_curation(curation, dict(state.items), pool, registry())
    assert final.summary != curation.summary
    assert any("unselected keys" in issue for issue in final.issues)


def test_valid_model_summary_for_the_final_set_is_kept():
    state = make_state()
    items = by_voice(state)
    keys = (items["a"].key, items["b"].key)
    curation = WeeklyCuration(
        keys, GOOD_SUMMARY, {keys[0]: "Argues unilateral restraint fails."}, True, covers=keys
    )
    selected, final = finalize_curation(curation, dict(state.items), list(state.items.values()), registry())
    assert [i.key for i in selected] == list(keys)
    assert final.summary == GOOD_SUMMARY
    assert final.reasons == {keys[0]: "Argues unilateral restraint fails."}
    assert final.issues == ()


def test_same_voice_is_bounded_and_synthesis_is_rewritten_for_the_kept_set():
    state = make_state(("a", "a", "a"))
    items = list(state.items.values())
    keys = tuple(item.key for item in items)
    text = "Alpha Writer's three essays, taken together, say the same thing."
    curation = WeeklyCuration(keys, text, {}, True, covers=keys)
    selected, final = finalize_curation(curation, dict(state.items), items, registry())

    assert len(selected) == WEEKLY_MAX_PER_VOICE == 1
    assert final.selected_keys == tuple(item.key for item in selected)
    assert final.summary != text
    assert final.summary.startswith("One Core piece")
    assert any("per-Voice limit" in issue for issue in final.issues)


def test_selection_never_exceeds_cap_and_dedupes_keys():
    state = make_state()
    items = list(state.items.values())
    keys = tuple(i.key for i in items) + (items[0].key,)
    selected, final = finalize_curation(
        WeeklyCuration(keys, "Four pieces.", {}, False), dict(state.items), items, registry()
    )
    assert len(selected) == WEEKLY_CAP
    assert len({i.key for i in selected}) == len(selected)


def test_set_shift_between_publish_attempts_rewrites_the_lead(tmp_path, monkeypatch):
    """A piece pruned between claim attempts must not stay in the printed synthesis."""
    state = make_state()
    items = by_voice(state)
    keys = [items["a"].key, items["b"].key]
    curator, models = gemini({"selected_keys": keys, "summary": GOOD_SUMMARY, "summary_covers": keys})
    state_path = tmp_path / "state.json"

    class FlakyStore(FileRoundupStore):
        def __init__(self, path):
            super().__init__(path)
            self.attempts = 0

        def publish(self, state, page_html, page_path, message):
            self.attempts += 1
            if self.attempts == 1:
                fresh = self.load()
                fresh.items.pop(keys[1], None)
                state_path.write_text(fresh.dumps(), encoding="utf-8")
                return False
            return super().publish(state, page_html, page_path, message)

    state_path.write_text(state.dumps(), encoding="utf-8")
    store = FlakyStore(state_path)
    code, page, notifier, saved = run_publish(tmp_path, monkeypatch, state, curator, store=store)

    assert code == 0 and store.attempts == 2
    assert len(models.calls) == 1
    assert page.count('class="piece"') == 1
    assert "Beta Writer" not in page.split("Worth your time")[0]
    assert saved.last_roundup.selection_keys == (keys[0],)
    assert len(notifier.sent) == 1


def test_render_never_prints_a_lead_written_for_a_different_set():
    state = make_state()
    items = by_voice(state)
    curation = WeeklyCuration(
        (items["a"].key, items["b"].key, items["c"].key), "Three-way synthesis.", {}, True
    )
    page = render_weekly(PERIOD, [items["a"]], registry(), curation)
    assert "Three-way synthesis." not in page
    assert page.count('class="piece"') == 1
    assert "Worth your time · 1 piece<" in page


# --- evidence strength -------------------------------------------------------------------


def test_evidence_posture_classification():
    assert fid.evidence_posture("Study finds internet use is associated with lower attendance") == fid.POSTURE_ASSOCIATION
    assert fid.evidence_posture("A randomized controlled trial of cash transfers") == fid.POSTURE_CAUSAL
    assert fid.evidence_posture("Notes on Italian cities") == fid.POSTURE_UNSPECIFIED
    assert fid.evidence_posture("") == fid.POSTURE_UNSPECIFIED


def test_causal_wording_for_association_only_source_is_blocked_but_hedged_is_allowed():
    piece = fid.Piece("k", "Religion online", ("Beth Marlow",), "Pub", fid.POSTURE_ASSOCIATION)
    assert fid.causal_overclaims("Marlow offers an explanatory account of religious decline.", [piece])
    assert fid.causal_overclaims("Beth Marlow shows the internet causes secularization.", [piece])
    assert not fid.causal_overclaims(
        "Marlow reports that internet use is associated with decline, and the evidence is not causal.", [piece]
    )
    # Sentences about other pieces, and sources with causal support, are untouched.
    other = fid.Piece("o", "Cash", ("Gina Ortiz",), "Pub", fid.POSTURE_CAUSAL)
    assert not fid.causal_overclaims("Ortiz's trial shows cash transfers cause higher savings.", [piece, other])
    assert not fid.causal_overclaims("Marlow explains.", [other])


def test_grounded_curator_blocks_causal_upgrade_from_association_excerpt(tmp_path, monkeypatch):
    state = make_state(("b", "c"))
    items = by_voice(state)
    keys = [items["b"].key, items["c"].key]
    descriptions = {
        keys[0]: (
            "New survey research finds that heavier internet use is associated with lower "
            "religious attendance, though the data are observational."
        )
    }
    models = FakeModels(
        {
            "selected_keys": keys,
            "summary": (
                "Beta Writer's piece offers an explanatory account of how the internet drives "
                "religious decline, while Gamma Writer takes up Canadian federalism."
            ),
            "summary_covers": keys,
            "reasons": {
                keys[0]: "Shows the internet causes people to leave religion.",
                keys[1]: "Argues provinces already hold most of the bargaining power.",
            },
        }
    )
    curator = GroundedGeminiWeeklyCurator(
        client=SimpleNamespace(models=models), model="gemini-test", descriptions=descriptions
    )
    _, page, _, _ = run_publish(tmp_path, monkeypatch, state, curator)

    payload = json.loads(models.calls[0]["contents"])
    assert {c["key"]: c["evidence_posture"] for c in payload["candidates"]}[keys[0]] == "association_only"
    assert "explanatory account" not in page and "drives" not in page and "causes" not in page
    # The unproblematic reason is still rendered; the overclaiming one is dropped.
    assert "provinces already hold most of the bargaining power" in page
    assert "leave religion" not in page


# --- generic filler ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Both pieces explore the evolving landscape of artificial intelligence.",
        "Alpha Writer provides substantive insights into a significant social trend.",
        "The piece prompts reflection on the profound societal implications of AI.",
        "The headline and excerpt suggest a substantive piece.",
    ],
)
def test_generic_filler_is_detected(text):
    assert fid.filler_hits(text)


def test_concrete_synthesis_is_not_flagged_as_filler():
    assert not fid.filler_hits(GOOD_SUMMARY)


def test_generic_summary_and_meta_reasons_do_not_reach_the_page(tmp_path, monkeypatch):
    state = make_state()
    items = by_voice(state)
    keys = [items["a"].key, items["b"].key]
    curator, _ = gemini(
        {
            "selected_keys": keys,
            "summary": "Alpha Writer and Beta Writer explore the evolving landscape of technology and society.",
            "summary_covers": keys,
            "reasons": {keys[0]: "The headline suggests a substantive piece.", keys[1]: "Reports a concrete survey result."},
        }
    )
    _, page, _, _ = run_publish(tmp_path, monkeypatch, state, curator)
    assert "evolving landscape" not in page and "headline suggests" not in page
    assert "Reports a concrete survey result." in page


def test_canonical_fallback_summary_always_passes_its_own_validation():
    state = make_state()
    pieces = [
        fid.Piece(i.key, i.title, ("Alpha Writer",), i.publication, fid.POSTURE_ASSOCIATION)
        for i in list(state.items.values())[:3]
    ]
    pieces[0] = fid.Piece("x", "Why religion explains and causes everything", ("Alpha Writer",), "Pub", fid.POSTURE_ASSOCIATION)
    summary = fid.canonical_summary(pieces)
    items = list(state.items.values())[:1]
    curation = WeeklyCuration(tuple(i.key for i in items), summary, {}, True)
    selected, final = finalize_curation(curation, dict(state.items), items, registry())
    assert selected and final.summary  # canonical lead is never rejected into an empty page


# --- synthesis input constraints (single call, prompt contract) --------------------------


def test_synthesis_prompt_constrains_inputs_and_makes_one_call():
    state = make_state()
    items = by_voice(state)
    keys = [items["a"].key]
    curator, models = gemini({"selected_keys": keys, "summary": "Alpha Writer argues restraint fails.", "summary_covers": keys})
    result = curator.curate(list(state.items.values()), registry(), period=PERIOD)

    assert len(models.calls) == 1
    payload = json.loads(models.calls[0]["contents"])
    rules = " ".join(payload["synthesis_rules"])
    assert "ONLY the selected pieces" in rules
    assert "association_only" in rules and "never 'causes'" in rules
    assert "quotation marks" in rules
    assert "unrelated" in rules and "Never invent a theme" in rules
    assert "evolving landscape" in rules  # banned filler is named to the model
    assert "summary_covers" in payload["output"]
    assert f"at most {WEEKLY_MAX_PER_VOICE}" in " ".join(payload["selection_rules"])
    for candidate in payload["candidates"]:
        assert set(candidate) >= {"key", "writer", "publication", "headline", "evidence_posture"}
    assert result.covers == tuple(keys) and result.model_used


def test_synthesis_input_is_bounded_to_the_candidate_pool():
    state = make_state(("a", "b", "c", "d"))
    items = list(state.items.values())
    curator, models = gemini({"selected_keys": [items[0].key], "summary": "Alpha Writer argues restraint fails."})
    curator.curate(items, registry(), period=PERIOD)
    payload = json.loads(models.calls[0]["contents"])
    assert {c["key"] for c in payload["candidates"]} == {i.key for i in items}
    assert all(c["writer"] for c in payload["candidates"])


@pytest.mark.parametrize(
    "text",
    [
        "Associated Press reports rents rose again this quarter.",
        "A paper from the American Economic Association on housing.",
        "An associate professor at MIT on chip supply.",
        "Survey data show households are spending less.",
    ],
)
def test_incidental_association_words_do_not_mark_a_piece_association_only(text):
    assert fid.evidence_posture(text) == fid.POSTURE_UNSPECIFIED


@pytest.mark.parametrize(
    "text",
    [
        "Religiosity is associated with lower internet use, an observational result.",
        "The study finds a correlation between the two.",
        "A link between sleep and mood, from cross-sectional data.",
    ],
)
def test_explicit_association_language_still_marks_a_piece_association_only(text):
    assert fid.evidence_posture(text) == fid.POSTURE_ASSOCIATION
