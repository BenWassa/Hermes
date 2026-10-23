"""Offline contract for #71: incident-level crime needs civic significance."""
from __future__ import annotations

import datetime as dt
import json
from types import SimpleNamespace

import pytest

from src import canada, crime
from src import curate as curate_mod
from src.curate import _curation_view, _gen_config, _trim_input

TODAY = dt.date(2026, 10, 22)


def _story(
    index: int,
    title: str,
    description: str = "",
    *,
    section: str = "toronto",
    coverage_lane: str = "",
) -> dict:
    return {
        "title": title,
        "description": description,
        "source": "Fixture News",
        "section_hint": section,
        "pub_date": "2026-10-22T08:00:00Z",
        "image": None,
        "link": f"https://example.com/{index}",
        "canonical_url": f"https://example.com/{index}",
        "coverage_lane": coverage_lane,
    }


def _filler(count: int, start: int = 1000) -> list[dict]:
    return [
        _story(start + i, f"Routine Toronto city story {i}", section="toronto") for i in range(count)
    ]


ISOLATED = (
    "Man and woman fatally shot outside a Toronto hospital",
    "Police believe the victims were married. Homicide detectives are investigating "
    "and say there is no ongoing threat to public safety.",
)


def isolated(index: int = 1) -> dict:
    return _story(index, *ISOLATED)


# --- the gate: low-significance incidents --------------------------------

def test_isolated_homicide_with_no_wider_significance_is_an_unsupported_incident():
    story = isolated()

    assert crime.is_incident(story)
    assert crime.significance_reasons(story) == ()
    assert crime.is_unsupported_incident(story)


@pytest.mark.parametrize(
    "description",
    [
        "Police say there is no threat to the public.",
        "Investigators say there is no ongoing risk to public safety.",
        "Police describe the attack as targeted and not random.",
    ],
)
def test_statements_that_there_is_no_continuing_threat_are_not_threat_signals(description):
    story = _story(1, "Man stabbed to death in Scarborough", description)

    assert crime.is_unsupported_incident(story)


def test_unsupported_incidents_are_demoted_behind_ordinary_news_in_bounded_input():
    incident = isolated(1)
    pool = [incident, *_filler(9)]

    selected = _trim_input(pool, total=9, today=TODAY)

    assert len(selected) == 9
    assert incident not in selected


def test_unsupported_incidents_are_withheld_from_the_model_input():
    incidents = [
        _story(i, f"Man shot dead in neighbourhood {i}", "Police are investigating.")
        for i in range(1, 6)
    ]

    selected = _trim_input(incidents + _filler(3), total=20, today=TODAY)

    assert crime.CRIME_INCIDENT_INPUT_CAP == 0
    assert not [story for story in selected if crime.is_unsupported_incident(story)]
    assert len(selected) == 3


def test_model_sees_an_isolated_incident_note_only_on_incident_records():
    view = _curation_view([isolated(1), *_filler(1)], TODAY)

    assert view[0]["crime_significance"].startswith("isolated incident")
    assert "crime_significance" not in view[1]


def test_canada_national_reserve_does_not_protect_an_unsupported_incident():
    incident = _story(
        1,
        "Woman stabbed to death in Ottawa",
        "Police are investigating.",
        section="world",
        coverage_lane=canada.CANADA_COVERAGE_LANE,
    )
    pool = [_story(i, f"World story {i}", section="world") for i in range(30)]

    selected = _trim_input(pool + [incident], total=10, today=TODAY)

    assert incident not in selected


# --- important exceptions stay eligible -----------------------------------

def test_same_incident_with_an_active_public_threat_is_eligible():
    story = _story(
        1,
        "Man fatally shot outside Toronto hospital, suspect still at large",
        "Police warn residents the gunman may be armed and dangerous.",
    )

    assert crime.significance_reasons(story)[0] == "active public threat"
    assert not crime.is_unsupported_incident(story)


def test_same_incident_as_part_of_a_documented_pattern_is_eligible():
    story = _story(
        1,
        "Fatal shooting is the latest in a string of shootings near Toronto hospitals",
        "Police are investigating whether the shootings are linked.",
    )

    assert "recurring pattern" in crime.significance_reasons(story)
    assert not crime.is_unsupported_incident(story)


def test_mass_casualty_and_disruption_are_eligible():
    mass = _story(1, "Mass shooting at Toronto plaza", "Several people were shot.")
    disruption = _story(
        2,
        "Stabbing at Union Station",
        "Service suspended on Line 1 and the station was evacuated.",
    )

    assert "multiple victims or mass casualty" in crime.significance_reasons(mass)
    assert "civic disruption" in crime.significance_reasons(disruption)


def test_court_policing_and_policy_consequences_are_eligible():
    story = _story(
        1,
        "SIU clears officer in fatal shooting, oversight review ordered",
        "The Special Investigations Unit said a police oversight review will follow.",
    )

    assert "policing, courts or policy" in crime.significance_reasons(story)
    assert not crime.is_unsupported_incident(story)


def test_trend_statistics_about_shootings_remain_eligible():
    story = _story(
        1,
        "Toronto shootings down 18 per cent so far this year, police data show",
        "Homicides are roughly flat compared with last year.",
    )

    assert crime.is_incident(story)
    assert "crime trend or statistics" in crime.significance_reasons(story)
    assert not crime.is_unsupported_incident(story)


def test_major_corruption_or_institutional_crime_story_is_never_gated():
    story = _story(
        1,
        "Provincial inquiry hears of bribery at city contract office",
        "Investigators allege a kickback scheme involving senior officials.",
    )

    assert not crime.is_incident(story)
    assert "crime_significance" not in _curation_view([story], TODAY)[0]


def test_supported_incidents_are_not_capped_and_carry_their_reason():
    supported = [
        _story(i, f"Man shot dead, suspect at large {i}", "Police warn the public.")
        for i in range(1, 6)
    ]

    selected = _trim_input(supported + _filler(2), total=20, today=TODAY)

    assert all(story in selected for story in supported)
    marker = _curation_view(supported[:1], TODAY)[0]["crime_significance"]
    assert marker == "civic significance: active public threat"


# --- human-interest details are not importance signals ---------------------

HUMAN_INTEREST = (
    " The 34-year-old father of three was days from his wedding, relatives called "
    "him a beloved coach, and his wife, a nurse, was also killed."
)


def test_vivid_victim_detail_alone_does_not_raise_priority():
    plain = _story(1, "Man fatally shot in Etobicoke", "Police are investigating.")
    vivid = _story(2, "Beloved father of three fatally shot in Etobicoke",
                   "Police are investigating." + HUMAN_INTEREST)

    assert crime.significance_reasons(plain) == ()
    assert crime.significance_reasons(vivid) == ()
    assert crime.is_unsupported_incident(vivid)
    assert _curation_view([vivid], TODAY)[0]["crime_significance"].startswith(
        "isolated incident"
    )


def test_human_interest_detail_does_not_change_a_supported_incidents_reasons():
    base = _story(1, "Man shot dead, suspect at large", "Police warn residents.")
    vivid = _story(2, "Man shot dead, suspect at large", "Police warn residents." + HUMAN_INTEREST)

    assert crime.significance_reasons(base) == crime.significance_reasons(vivid)


def test_relationship_is_secondary_unless_it_changes_the_substantive_interpretation():
    married_only = _story(
        1, "Couple fatally shot outside hospital", "Police believe the victims were married."
    )
    ipv = _story(
        2,
        "Couple fatally shot outside hospital",
        "Police believe the victims were married and are investigating the deaths "
        "as intimate partner violence.",
    )
    murder_suicide = _story(
        3,
        "Couple found dead in murder-suicide investigation",
        "Police believe the victims were married.",
    )

    assert crime.is_unsupported_incident(married_only)
    assert crime.significance_reasons(ipv) == ("broader public issue",)
    assert crime.significance_reasons(murder_suicide) == ("broader public issue",)


# --- scope: everything else is unaffected ---------------------------------

def test_non_crime_local_stories_are_unaffected():
    stories = [
        _story(1, "TTC fare changes approved by city council", "Riders will pay more in January."),
        _story(2, "Raptors shot 52 per cent in a win over Boston", "A big night downtown."),
        _story(3, "Hospital wait times in Toronto reach record highs", "Emergency rooms are full."),
    ]

    assert not any(crime.is_incident(story) for story in stories)
    assert crime.bound_unsupported_incidents(stories) == (stories, 0)
    assert all("crime_significance" not in item for item in _curation_view(stories, TODAY))


def test_world_wire_violence_opinion_and_sports_are_out_of_scope():
    war = _story(1, "Missile strike kills dozens in shooting of aid convoy", "", section="world")
    op_ed = _story(2, "Why the latest shooting should change our politics", "", section="opinion")

    assert not crime.is_incident(war)
    assert not crime.is_incident(op_ed)


def test_only_incident_specific_violence_triggers_the_gate_not_bare_killed():
    crash = _story(1, "Pedestrian killed in collision on Bloor", "Police say the driver stayed.")
    fire = _story(2, "Two killed in apartment fire", "Fire crews are investigating.")

    assert not crime.is_incident(crash)
    assert not crime.is_incident(fire)


# --- budgets: size, dedupe, idempotency, single model call ----------------

def test_input_bound_dedupe_and_idempotency_are_preserved():
    incident = isolated(1)
    duplicate = dict(incident, link="https://example.com/dup")
    duplicate["canonical_url"] = incident["canonical_url"]
    pool = [incident, duplicate, *_filler(30)]

    first = _trim_input(pool, total=12, today=TODAY)
    second = _trim_input(pool, total=12, today=TODAY)

    assert len(first) <= 12
    assert sum(story["canonical_url"] == incident["canonical_url"] for story in first) <= 1
    assert first == second


def test_quiet_pool_without_crime_selects_exactly_as_before():
    pool = _filler(15)

    assert _trim_input(pool, total=10, today=TODAY) == pool[:10]


def test_curate_withholds_unsupported_incidents_and_makes_one_model_call(monkeypatch):
    calls: list[dict] = []
    incident = isolated(1)

    class Model:
        def generate_content(self, *, model, contents, config):
            calls.append({"contents": contents, "system": config.system_instruction})
            payload = {
                "sections": [
                    {"id": "front", "label": "Front Page", "stories": [
                        {"id": "f1", "lead": True, "headline": "Routine",
                         "link": "https://example.com/1000"},
                    ]},
                    {"id": "toronto", "label": "Toronto", "stories": [
                        {"id": "t1", "lead": True, "headline": "Routine",
                         "link": "https://example.com/1000"},
                        {"id": "t2", "lead": False, "headline": "Routine two",
                         "link": "https://example.com/1001"},
                    ]},
                ]
            }
            return SimpleNamespace(text=json.dumps(payload), model_version=model,
                                   usage_metadata=None)

    monkeypatch.setattr(curate_mod, "_client", lambda: SimpleNamespace(models=Model()))

    edition = curate_mod.curate([incident, *_filler(2)], today=TODAY)

    assert len(calls) == 1
    assert incident["title"] not in calls[0]["contents"]
    assert "CRIME AND INCIDENT SIGNIFICANCE" in calls[0]["system"]
    sections = {section["id"]: section["stories"] for section in edition["sections"]}
    assert [s["id"] for s in sections["toronto"]] == ["t1", "t2"]
    assert all(s["link"] != incident["link"] for st in sections.values() for s in st)


def test_system_prompt_states_the_significance_and_human_interest_contract():
    system = _gen_config(TODAY).system_instruction

    assert "CRIME AND INCIDENT SIGNIFICANCE" in system
    assert "never sufficient" in system
    assert "headline hook" in system
    assert "stand in for trend evidence" in system


# --- post-model placement guard -------------------------------------------

def _raw_sections(incident: dict, other: dict) -> list[dict]:
    return [
        {"id": "front", "stories": [
            {"id": "a", "lead": True, "link": incident["link"]},
            {"id": "b", "lead": False, "link": other["link"]},
        ]},
        {"id": "toronto", "stories": [
            {"id": "c", "lead": True, "link": incident["link"]},
            {"id": "d", "lead": False, "link": other["link"]},
        ]},
    ]


def test_enforce_placement_removes_from_front_and_demotes_lead_without_growth():
    incident, other = isolated(1), _filler(1)[0]
    sections = _raw_sections(incident, other)

    affected = crime.enforce_placement(sections, [incident, other])

    assert affected == 2
    assert [s["id"] for s in sections[0]["stories"]] == ["b"]
    assert [s["id"] for s in sections[1]["stories"]] == ["d", "c"]
    assert sections[1]["stories"][1]["lead"] is False
    assert sum(len(s["stories"]) for s in sections) == 3


def test_enforce_placement_is_idempotent_and_leaves_supported_incidents_alone():
    incident, other = isolated(1), _filler(1)[0]
    sections = _raw_sections(incident, other)
    crime.enforce_placement(sections, [incident, other])
    snapshot = json.dumps(sections, sort_keys=True)

    crime.enforce_placement(sections, [incident, other])
    assert json.dumps(sections, sort_keys=True) == snapshot

    threat = _story(5, "Man shot dead, suspect at large", "Police warn residents.")
    keep = _raw_sections(threat, other)
    assert crime.enforce_placement(keep, [threat, other]) == 0
    assert [s["id"] for s in keep[0]["stories"]] == ["a", "b"]
    assert keep[1]["stories"][0]["lead"] is True


# --- review fixes: false positives in the matcher (#85) ---------------------

@pytest.mark.parametrize(
    "title, description",
    [
        ("Carney announces ban on assault-style firearms", "Gun owners will have two years to comply."),
        ("Liberals table assault weapons buyback legislation", ""),
        ("Cameras roll as shooting begins on new Toronto film", "The production will close streets."),
        ("Raptors' shooting woes continue in loss", "Toronto shot 38 per cent from the floor."),
    ],
)
def test_policy_film_and_sports_wording_is_not_an_incident(title, description):
    story = _story(1, title, description)

    assert not crime.is_incident(story)
    assert not crime.is_unsupported_incident(story)
    assert crime.bound_unsupported_incidents([story]) == ([story], 0)
    assert "crime_significance" not in _curation_view([story], TODAY)[0]


def test_gun_control_policy_story_is_never_an_isolated_incident():
    story = _story(
        1,
        "Carney announces ban on assault-style firearms after shooting",
        "Police chiefs welcomed the gun control measures.",
    )

    assert crime.is_incident(story)
    assert "policing, courts or policy" in crime.significance_reasons(story)
    assert not crime.is_unsupported_incident(story)


@pytest.mark.parametrize(
    "title, description",
    [
        ("Man shot in Etobicoke", "Police say the shooting was reported overnight."),
        ("Shooting leaves woman dead in Scarborough", ""),
        ("Two wounded in shooting near Jane and Finch", ""),
        ("Man shot dead in North York", ""),
    ],
)
def test_violent_shootings_are_still_incidents(title, description):
    assert crime.is_incident(_story(1, title, description))


def test_boilerplate_urging_for_information_is_not_an_active_threat():
    story = _story(
        1,
        "Man fatally shot in Etobicoke",
        "Police are urging anyone with information to come forward.",
    )

    assert crime.significance_reasons(story) == ()
    assert crime.is_unsupported_incident(story)


@pytest.mark.parametrize(
    "description",
    [
        "Police are urging residents to avoid the area while the suspect is sought.",
        "Residents were urged to stay indoors and lock their doors.",
    ],
)
def test_urging_residents_to_take_precautions_is_an_active_threat(description):
    story = _story(1, "Man fatally shot in Etobicoke", description)

    assert crime.significance_reasons(story)[0] == "active public threat"


@pytest.mark.parametrize(
    "description",
    [
        "Police say the shooting is linked to a dispute between neighbours.",
        "The victim was connected to the suspect through work.",
    ],
)
def test_ordinary_link_wording_is_not_a_recurring_pattern(description):
    story = _story(1, "Man fatally shot in Etobicoke", description)

    assert crime.significance_reasons(story) == ()
    assert crime.is_unsupported_incident(story)


@pytest.mark.parametrize(
    "description",
    [
        "Police say the shooting is linked to earlier incidents in the area.",
        "Investigators are probing linked incidents across the east end.",
        "The attack was connected to a series of robberies.",
    ],
)
def test_real_pattern_wording_is_still_a_recurring_pattern(description):
    story = _story(1, "Man fatally shot in Etobicoke", description)

    assert "recurring pattern" in crime.significance_reasons(story)


def test_opinion_items_are_out_of_scope_by_section_or_genre():
    column = _story(
        1,
        "Her murder shows our justice system failed women",
        "A column on bail and violence.",
        section="world",
        coverage_lane=canada.CANADA_COVERAGE_LANE,
    )
    column["content_genre"] = "opinion"
    sectioned = _story(
        2, "Why the latest stabbing should change our politics", "",
        section="opinion", coverage_lane=canada.CANADA_COVERAGE_LANE,
    )
    news = dict(column, content_genre="news")
    no_genre = {k: v for k, v in column.items() if k != "content_genre"}

    assert not crime.in_scope(column)
    assert not crime.is_unsupported_incident(column)
    assert not crime.is_unsupported_incident(sectioned)
    assert crime.bound_unsupported_incidents([column, sectioned]) == ([column, sectioned], 0)
    assert "crime_significance" not in _curation_view([column], TODAY)[0]
    assert crime.is_unsupported_incident(news)
    assert crime.is_unsupported_incident(no_genre)
