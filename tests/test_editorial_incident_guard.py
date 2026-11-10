"""Issue #111 Nov 2 separated crash/SIU sources versus mixed model card."""
from __future__ import annotations

import datetime as dt
from copy import deepcopy

from src import curate
from src.editorial_incident_guard import enforce_incident_source_boundary

CRASH = {
    "title": "Four teens from Mississauga, Brampton, Milton killed in early morning crash near Guelph, police say",
    "description": "Police said that it is too early to determine the cause of the crash and the investigation is ongoing.",
    "link": "https://www.thestar.com/news/gta/four-teens-from-mississauga-brampton-milton-killed-in-early-morning-crash-near-guelph-police-say/article_12afb19d-00be-4a76-bf72-ab0fcf63c4b3.html",
    "pub_date": "2026-11-01T17:30:00Z",
    "section_hint": "toronto",
}
SIU = {
    "title": "Police watchdog investigating after boy's arm fractured during arrest over suspected fare evasion",
    "description": "Five teens were arrested; a separate watchdog investigation is underway.",
    "link": "https://www.thestar.com/news/gta/police-watchdog-investigating-after-boy-s-arm-fractured-during-arrest-over-suspected-fare-evasion/article_8a7473a3-92d1-48d4-aa16-22b8d1d2bdab.html",
    "pub_date": "2026-11-01T12:00:00Z",
    "section_hint": "toronto",
}
HEADLINE = ("Four teens killed in early morning crash near Guelph, "
            "police watchdog investigates fractured arm during fare evasion arrest")


def card(link=CRASH["link"], headline=HEADLINE):
    return {
        "headline": headline, "sub": "Police watchdog probes fare evasion arrest",
        "summary": "Four teens died in a crash. A boy's arm was fractured during a fare evasion arrest.",
        "analysis": "The crash and arrest raise new questions.", "link": link, "lead": True,
    }


def apply(one, candidates):
    return enforce_incident_source_boundary([{"id": "toronto", "stories": [one]}], candidates)


def test_nov2_two_disjoint_incidents_never_share_one_crash_link():
    contaminated = card()
    before_link = contaminated["link"]
    stats = apply(contaminated, [CRASH, SIU])
    assert stats == {"checked": 1, "repaired": 1, "abstained": 0}
    assert contaminated["headline"] == CRASH["title"]
    assert contaminated["summary"] == CRASH["description"]
    assert contaminated["sub"] == CRASH["description"]
    assert contaminated["analysis"] is None
    assert contaminated["link"] == before_link
    assert contaminated["lead"] is True


def test_inverse_siu_article_does_not_inherit_unrelated_crash():
    contaminated = card(SIU["link"])
    assert apply(contaminated, [CRASH, SIU])["repaired"] == 1
    assert contaminated["headline"] == SIU["title"]
    assert contaminated["summary"] == SIU["description"]


def test_related_same_event_arrest_after_crash_is_not_rewritten():
    related = dict(SIU, title="Driver arrested after the Guelph crash",
                   description="Police arrested the driver after the crash near Guelph")
    c = card()
    assert apply(c, [CRASH, related])["repaired"] == 0
    assert c["headline"] == HEADLINE


def test_source_explicitly_covering_both_incidents_is_not_rewritten():
    joined = dict(CRASH, title="Crash and separate watchdog arrest probe reported")
    c = card()
    assert apply(c, [joined, SIU])["repaired"] == 0


def test_no_alternative_source_does_not_infer_contamination():
    c = card()
    assert apply(c, [CRASH])["repaired"] == 0


def test_non_incident_overlap_is_not_enough():
    c = card(headline="Four teens killed in Guelph crash; city debates transport policy")
    c["summary"] = "Traffic safety will be discussed by councillors."
    assert apply(c, [CRASH, SIU])["repaired"] == 0


def test_unmatched_source_abstains_without_relinking():
    c = card(link="https://unmatched.example.org/story")
    assert apply(c, [CRASH, SIU]) == {"checked": 0, "repaired": 0, "abstained": 1}
    assert c["headline"] == HEADLINE


def test_curation_pipeline_calls_source_boundary_after_link_restoration(monkeypatch):
    stages = []

    def record_restore(sections, pool, day):
        stages.append("restore")
    def record_guard(sections, pool):
        stages.append("incident")
        return {"checked": 0, "repaired": 0, "abstained": 0}
    def record_facts(sections, pool, day):
        stages.append("facts")

    monkeypatch.setattr(curate, "_client", lambda: object())
    monkeypatch.setattr(curate, "_trim_input", lambda stories, today: stories)
    monkeypatch.setattr(curate, "_call", lambda *args, **kwargs: {
        "sections": [{"id": "world", "stories": [card(headline="Normal world headline")]}]})
    monkeypatch.setattr(curate, "restore_source_metadata", record_restore)
    monkeypatch.setattr(curate, "enforce_incident_source_boundary", record_guard)
    monkeypatch.setattr(curate, "enforce_source_claims", record_facts)
    curate.curate([CRASH, SIU], today=dt.date(2026, 11, 2))
    assert stages == ["restore", "incident", "facts"]
