"""Targeted factual contradictions, adversarial abstentions, no external calls."""
from __future__ import annotations

import datetime as dt

from src.editorial_fact_guard import enforce_source_claims

DAY = dt.date(2026, 10, 25)
LINK = "https://example.org/election/2026/10/25/story"


def candidate(title, description):
    return {
        "title": title, "description": description, "pub_date": "2026-10-25T10:00:00Z",
        "link": LINK, "canonical_url": LINK,
    }


def card(headline="Election update", *, summary="A first development."):
    return {"headline": headline, "summary": summary, "analysis": None,
            "sub": None, "link": LINK, "lead": True}


def guard(c, source, day=DAY):
    sections = [{"id": "front", "stories": [c]}]
    stats = enforce_source_claims(sections, [source], day)
    return c, stats


def test_future_election_reported_as_underway_today_is_withheld_not_corrected():
    source = candidate(
        "Knesset election set for October 27, 2026",
        "Election scheduled for October 27, 2026. Polls have not opened.",
    )
    c = card(summary="Israel's election is underway today. Parties are competing for seats.")
    c, stats = guard(c, source)
    assert c["summary"] == "Parties are competing for seats."
    assert stats == {"checked": 1, "flagged": 1, "sentences_withheld": 1, "abstained": 0}


def test_future_election_in_lead_headline_uses_only_same_source_title():
    source = candidate(
        "National election set for October 27, 2026",
        "Election scheduled for October 27, 2026.",
    )
    c = card(headline="National election is today", summary="Campaign preparations continue.")
    c, stats = guard(c, source)
    assert c["headline"] == source["title"]
    assert stats["flagged"] == 1


def test_reelected_incumbent_is_not_called_returned_to_power():
    source = candidate(
        "Incumbent president Lula re-elected to fourth term",
        "Incumbent president Lula has won another term.",
    )
    c = card(summary="Lula secured another term.",
             headline="Lula wins reelection")
    c["analysis"] = "Lula's return to power may change alliances. His new term starts next year."
    c, stats = guard(c, source)
    assert c["analysis"] == "His new term starts next year."
    assert c["summary"] == "Lula secured another term."
    assert stats["sentences_withheld"] == 1


def test_ambiguous_incumbency_does_not_rewrite_history_or_make_up_current_roles():
    source = candidate(
        "Lula wins presidential election",
        "The result gives the president another term; other candidates conceded.",
    )
    c = card(summary="Lula's return to power shifts political alliances.")
    c, stats = guard(c, source)
    assert c["summary"] == "Lula's return to power shifts political alliances."
    assert stats["abstained"] == 1
    assert stats["flagged"] == 0


def test_incumbent_return_during_prior_election_is_historical_not_a_current_reelection():
    source = candidate(
        "Incumbent president Lula re-elected",
        "Reelection confirmed by officials.",
    )
    c = card(summary="Lula returned to power in 2022. He won a new term today.")
    c, _ = guard(c, source)
    # Historical context is not contradictory to incumbent reelection today.
    assert c["summary"] == "Lula returned to power in 2022. He won a new term today."


def test_source_election_date_only_suppresses_assertions_when_future():
    source = candidate("National election set for October 27, 2026", "")
    c = card(summary="The election is today.")
    c, stats = guard(c, source, day=dt.date(2026, 10, 27))
    assert c["summary"] == "The election is today."
    assert stats["flagged"] == 0


def test_wrong_actor_and_source_conflict_do_not_create_unverified_new_facts():
    source = candidate(
        "Incumbent president Lula re-elected",
        "Election scheduled for October 27, 2026.",
    )
    c = card(summary="Another candidate is returning to power. The future is uncertain.")
    c, stats = guard(c, source)
    assert c["summary"] == "Another candidate is returning to power. The future is uncertain."
    assert stats["flagged"] == 0


def test_unmatched_source_and_unsupported_numerical_result_abstain():
    source = candidate("Candidate A wins first round", "Candidate A led Candidate B by 48 to 45.")
    c = card(summary="Candidate B led Candidate A in the first round.")
    c["link"] = "https://unmatched.example/news"
    sections = [{"id": "world", "stories": [c]}]
    stats = enforce_source_claims(sections, [source], DAY)
    assert stats["abstained"] == 1
    assert c["summary"] == "Candidate B led Candidate A in the first round."


def test_cross_publisher_matching_never_uses_title_similarity():
    source = candidate("Election scheduled for October 27, 2026", "")
    c = card("Election scheduled for October 27, 2026",
             summary="The election is underway today.")
    c["link"] = "https://another.org/election/2026/10/25/story"
    _, stats = guard(c, source)
    assert stats["flagged"] == 0
    assert stats["abstained"] == 1


def test_summary_with_all_sentences_contradicted_falls_back_to_source_headline():
    source = candidate("Knesset election set for October 27, 2026",
                       "The vote has not begun.")
    c = card(summary="The election is today.")
    c, stats = guard(c, source)
    assert c["summary"] == source["title"]
    assert stats["sentences_withheld"] == 1
