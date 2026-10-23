"""Toronto section integrity (#83): off-city items out, section never missing.

Fixtures reproduce the verified baseline defects HA-03 / HA-04
(research/historical-audit/BASELINE_2026-10-22.md). Titles and links are the
published ones; descriptions are neutral stand-ins for the source abstracts.
"""

from __future__ import annotations

import datetime as dt
import logging

import pytest

from src import canada, toronto
from src.curate import _guard_toronto_section, _normalize_edition

TODAY = dt.date(2026, 10, 22)
CAP = 4


def cand(title, link, *, source="Perigon Wire", hint="world", lane="", description="", pub="2026-10-22T09:00:00Z", image=None):
    return {
        "title": title, "description": description, "source": source,
        "section_hint": hint, "pub_date": pub, "image": image, "link": link,
        "canonical_url": link, "coverage_lane": lane, "provider": "perigon",
    }


def card(candidate, n, *, summary="Model summary.", lead=False):
    return {
        "id": f"x{n}", "lead": lead, "kicker": "CANADA", "headline": candidate["title"],
        "sub": None, "summary": summary, "analysis": "Why it matters." if lead else None,
        "time": "7:00 AM", "tag": None, "sensitivity": False,
        "image": candidate["image"], "link": candidate["link"],
    }


NATIONAL = canada.CANADA_COVERAGE_LANE

# --- Baseline HA-04 off-city items -----------------------------------------
GOOSE_BAY = cand(
    "REPEAT Media Advisory - Infrastructure announcement in Happy Valley-Goose Bay",
    "https://www.newswire.ca/news-releases/-r-e-p-e-a-t-media-advisory-infrastructure-announcement-in-happy-valley-goose-bay--833173026.html",
    lane=NATIONAL, description="HAPPY VALLEY-GOOSE BAY, NL, Oct. 14, 2026 /CNW/ - Federal and provincial officials will make an announcement in Labrador.",
)
MORDEN = cand(
    "Ernie Epp brings municipal experience and new priorities to Morden mayoral race",
    "https://pembinavalleyonline.com/articles/ernie-epp-brings-municipal-experience-and-new-priorities-to-morden-mayoral-race",
    lane=NATIONAL, description="The candidate for mayor in Manitoba's Pembina Valley outlines his priorities.",
)
GEORGE_GORDON = cand(
    "George Gordon First Nation walks to remember 30th anniversary of demolishing residential school",
    "https://www.ctvnews.ca/regina/article/george-gordon-first-nation-walks-to-remember-30th-anniversary-of-demolishing-residential-school/",
    description="Community members in Saskatchewan gathered for the anniversary.",
)
ALBERTA_RAT = cand(
    "Alberta rat patrol: the Canadian province that has kept rats out for decades",
    "https://www.theguardian.com/world/2026/sep/25/alberta-canada-rat-patrol",
    source="The Guardian", description="Alberta's pest control programme is the envy of the world.",
)
THUNDER_BAY = cand(
    "City of Thunder Bay promised Victoriaville project completion by October 2026",
    "https://www.netnewsledger.com/2026/10/22/city-of-thunder-bay-promised-victoriaville-project-completion-by-october-2026/",
    description="A northwestern Ontario downtown revitalization project is behind schedule.",
)
QUEBEC = cand(
    "A dangerous liaison looms in Quebec",
    "https://canadiandimension.com/articles/view/a-dangerous-liaison-looms-in-quebec",
    description="Provincial politics in Quebec ahead of the next election.",
)
NAV_CANADA = cand(
    "NAV CANADA reports summer-long drop in flight delays at Canada's busiest airports",
    "https://www.newswire.ca/news-releases/nav-canada-reports-summer-long-drop-in-flight-delays-at-canada-s-busiest-airports-806450109.html",
    lane=NATIONAL,
    description="OTTAWA, ON, Sept. 28, 2026 /CNW/ - Delays fell at airports in Vancouver, Toronto Pearson and Montreal.",
)
OFF_CITY = [GOOSE_BAY, MORDEN, GEORGE_GORDON, ALBERTA_RAT, THUNDER_BAY, QUEBEC, NAV_CANADA]

# --- Genuine Toronto / GTA-adjacent stories ---------------------------------
WAYMO = cand(
    "Waymo announces plans to launch driverless taxis in Toronto, but humans will be at the wheel first",
    "https://www.thestar.com/news/gta/waymo-announces-plans-to-launch-driverless-taxis-in-toronto-but-humans-will-be-at-the-wheel-first/article_2f6f3623.html",
    source="Toronto Star GTA", hint="toronto",
)
SANTA_FUND = cand(
    "The Star's Santa Claus Fund turns 120. It's our turn to take part in this tradition of kindness",
    "https://www.thestar.com/initiatives/santa-claus-fund/the-star-s-santa-claus-fund-turns-120.html",
    source="Toronto Star GTA", hint="toronto",
)
BIKE_LANES = cand(
    "Health-care workers urge Doug Ford to quash plan to remove bike lanes in open letter",
    "https://www.thestar.com/news/gta/health-care-workers-urge-doug-ford-to-quash-plan.html",
    source="CBC Toronto", hint="toronto",
)
PERIGON_TORONTO = cand(
    "Toronto council weighs 2027 transit levy", "https://example.com/toronto-levy",
    description="City hall debates funding.",
)
MISSISSAUGA = cand(
    "Mississauga hospital opens new emergency wing", "https://example.com/mississauga-er",
    source="Brampton Guardian",
)
BODY_ONLY = cand(
    "Province unveils plan to cut hospital wait times", "https://example.com/waits",
    description="The plan will be tested first at sites in the GTA.",
)
DATELINE = cand(
    "Summer festival lineup announced", "https://example.com/festival",
    description="TORONTO, Oct. 22, 2026 /CNW/ - A festival returns to the waterfront.",
)


def sections_with(toronto_cards, **others):
    out = [{"id": "front", "label": "Front Page", "stories": [
        {"id": "f1", "lead": True, "headline": "Front", "link": "https://example.com/front", "analysis": "A"}]}]
    if toronto_cards is not None:
        out.append({"id": "toronto", "label": "Toronto", "stories": toronto_cards})
    for sid, stories in others.items():
        out.append({"id": sid, "label": sid.title(), "stories": stories})
    return out


def section(sections, sid):
    return next((x for x in sections if x["id"] == sid), None)


def toronto_links(sections):
    return [s["link"] for s in section(sections, "toronto")["stories"]]


# --- signal rules ------------------------------------------------------------

@pytest.mark.parametrize("off", OFF_CITY, ids=lambda c: c["title"][:30])
def test_baseline_off_city_items_have_no_toronto_signal(off):
    assert toronto.toronto_signal(card(off, 1), off) == ""


def test_nav_canada_release_listing_toronto_among_cities_is_not_toronto():
    # The body names Toronto Pearson, but other cities and a national marker veto it.
    assert toronto.toronto_signal({}, NAV_CANADA) == ""


@pytest.mark.parametrize(
    "good,reason",
    [(WAYMO, "feed"), (SANTA_FUND, "feed"), (BIKE_LANES, "feed"),
     (PERIGON_TORONTO, "headline"), (MISSISSAUGA, "headline"),
     (DATELINE, "dateline"), (BODY_ONLY, "body")],
)
def test_genuine_toronto_and_gta_items_keep_a_signal(good, reason):
    assert toronto.toronto_signal(card(good, 1), good) == reason


def test_canada_lane_item_from_a_toronto_named_source_is_not_trusted_as_feed():
    sneaky = dict(MORDEN, source="CBC Toronto", coverage_lane=NATIONAL)
    assert toronto.toronto_signal({}, sneaky) == ""


# --- section enforcement -----------------------------------------------------

def test_off_city_items_leave_toronto_and_genuine_ones_stay():
    pool = OFF_CITY + [WAYMO, SANTA_FUND, BIKE_LANES, PERIGON_TORONTO]
    cards = [card(c, i) for i, c in enumerate([GOOSE_BAY, WAYMO, MORDEN, SANTA_FUND], 1)]

    out, stats = toronto.enforce_toronto_section(sections_with(cards), pool, TODAY)

    links = toronto_links(out)
    assert WAYMO["link"] in links and SANTA_FUND["link"] in links
    assert GOOSE_BAY["link"] not in links and MORDEN["link"] not in links
    assert stats["kept"] == 2 and stats["reassigned"] + stats["dropped"] == 2
    # Edition size is refilled from Toronto-intake candidates only. The Perigon
    # item has a Toronto headline but came through a World hint, so keyword
    # evidence alone does not qualify it for backfill.
    assert len(links) == 3
    assert BIKE_LANES["link"] in links and PERIGON_TORONTO["link"] not in links


def test_every_baseline_off_city_item_is_removed_even_if_all_seven_were_placed():
    pool = OFF_CITY + [WAYMO, SANTA_FUND, BIKE_LANES]
    cards = [card(c, i) for i, c in enumerate(OFF_CITY, 1)]

    out, _ = toronto.enforce_toronto_section(sections_with(cards), pool, TODAY)

    assert not {c["link"] for c in OFF_CITY} & set(toronto_links(out))
    assert len(toronto_links(out)) == 3  # only three genuine candidates exist


def test_reassignment_goes_to_the_source_desk_and_preserves_canada_coverage():
    biz = dict(NAV_CANADA, section_hint="business")
    out, stats = toronto.enforce_toronto_section(
        sections_with([card(MORDEN, 1, lead=True), card(biz, 2), card(WAYMO, 3)], world=[], business=[]),
        [MORDEN, biz, WAYMO], TODAY,
    )
    assert MORDEN["link"] in [s["link"] for s in section(out, "world")["stories"]]
    assert biz["link"] in [s["link"] for s in section(out, "business")["stories"]]
    moved = section(out, "world")["stories"][0]
    assert moved["lead"] is False and moved["analysis"] is None
    assert stats["reassigned"] == 2 and stats["dropped"] == 0


def test_reassignment_creates_missing_desk_in_canonical_order():
    out, _ = toronto.enforce_toronto_section(
        sections_with([card(MORDEN, 1), card(WAYMO, 2)], business=[{"id": "b1", "link": "https://example.com/b"}]),
        [MORDEN, WAYMO], TODAY,
    )
    assert [s["id"] for s in out] == ["front", "toronto", "world", "business"]


def test_full_target_desk_drops_instead_of_exceeding_its_cap():
    world = [{"id": f"w{i}", "link": f"https://example.com/w{i}"} for i in range(4)]
    out, stats = toronto.enforce_toronto_section(
        sections_with([card(MORDEN, 1), card(WAYMO, 2)], world=world), [MORDEN, WAYMO], TODAY
    )
    assert len(section(out, "world")["stories"]) == 4
    assert stats["dropped"] == 1 and stats["reassigned"] == 0


def test_unmatched_story_is_judged_on_its_own_text():
    ghost = {"id": "g", "lead": False, "headline": "Manitoba flood watch widens", "summary": "Rivers rise.",
             "link": "https://example.com/not-in-pool"}
    fine = {"id": "h", "lead": False, "headline": "TTC announces fare review", "summary": "x",
            "link": "https://example.com/also-not-in-pool"}
    out, _ = toronto.enforce_toronto_section(sections_with([ghost, fine]), [WAYMO], TODAY)
    assert "https://example.com/also-not-in-pool" in toronto_links(out)
    assert "https://example.com/not-in-pool" not in toronto_links(out)


# --- HA-03: the missing section ---------------------------------------------

def test_missing_toronto_section_is_filled_from_the_toronto_pool():
    mississauga = dict(MISSISSAUGA, section_hint="toronto")
    pool = OFF_CITY + [WAYMO, SANTA_FUND, BIKE_LANES, mississauga]

    out, stats = toronto.enforce_toronto_section(sections_with(None), pool, TODAY)

    assert [s["id"] for s in out] == ["front", "toronto"]
    links = toronto_links(out)
    assert len(links) == CAP == stats["backfilled"]
    assert set(links) <= {c["link"] for c in (WAYMO, SANTA_FUND, BIKE_LANES, mississauga)}
    assert not {c["link"] for c in OFF_CITY} & set(links)


def test_empty_toronto_section_is_filled_too():
    out, _ = toronto.enforce_toronto_section(sections_with([]), [WAYMO], TODAY)
    assert toronto_links(out) == [WAYMO["link"]]


def test_backfill_cards_are_plain_source_metadata_with_edition_schema():
    pub = dict(WAYMO, description="Waymo says testing starts next year.",
               pub_date="2026-10-22T11:30:00Z", image="https://img/x.jpg")
    out, _ = toronto.enforce_toronto_section(sections_with(None), [pub], TODAY)
    filled = section(out, "toronto")["stories"][0]
    assert filled["headline"] == pub["title"] and filled["link"] == pub["link"]
    assert filled["summary"] == "Waymo says testing starts next year."
    assert filled["analysis"] is None and filled["kicker"] == "TORONTO"
    assert filled["time"] == "7:30 AM" and filled["image"] == "https://img/x.jpg"
    assert {"id", "lead", "kicker", "headline", "sub", "summary", "analysis", "time", "tag",
            "sensitivity", "image", "link"} <= set(filled)


def test_backfill_skips_stories_already_in_the_paper_near_duplicates_and_opinion():
    near_dupe = cand("Waymo plans driverless taxis for Toronto streets", "https://example.com/other-waymo",
                     source="CBC Toronto", hint="toronto")
    opinion = cand("Why Toronto needs a new plan", "https://www.thestar.com/opinion/contributors/why-toronto.html",
                   source="Toronto Star GTA", hint="toronto")
    front_dupe = cand("Rent report lands", "https://example.com/rent", source="CBC Toronto", hint="toronto")
    fresh = cand("New library branch opens", "https://example.com/library", source="CBC Toronto", hint="toronto")
    sections = [{"id": "front", "label": "Front Page", "stories": [
        {"id": "f1", "headline": "Waymo plans driverless taxis for Toronto streets", "link": "https://example.com/f"},
        {"id": "f2", "headline": "Rent report lands", "link": front_dupe["link"]},
    ]}]
    out, _ = toronto.enforce_toronto_section(sections, [near_dupe, opinion, front_dupe, fresh], TODAY)
    assert toronto_links(out) == [fresh["link"]]


def test_backfill_prefers_non_violent_items_and_marks_sensitivity():
    violent = cand("Man killed in Scarborough shooting", "https://example.com/v", source="CBC Toronto", hint="toronto",
                   description="Police warn the public; suspect at large.")
    calm = cand("Scarborough library reopens", "https://example.com/c", source="CBC Toronto", hint="toronto")
    out, _ = toronto.enforce_toronto_section(sections_with(None), [violent, calm], TODAY)
    stories = section(out, "toronto")["stories"]
    assert [s["link"] for s in stories] == [calm["link"], violent["link"]]
    assert [s["sensitivity"] for s in stories] == [False, True]


# --- review findings: backfill must not import keyword look-alikes ------------

HAMILTON_F1 = cand("Lewis Hamilton wins Mexican Grand Prix", "https://example.com/f1", hint="world")
GTA_GAME = cand("GTA VI delayed again, Rockstar says", "https://example.com/gta6", hint="world")
TSX = cand("S&P/TSX closes higher as Toronto stock index gains", "https://example.com/tsx", hint="business")


def test_backfill_ignores_keyword_lookalikes_from_world_and_business():
    calm = cand("New library branch opens", "https://example.com/library", source="CBC Toronto", hint="toronto")
    out, stats = toronto.enforce_toronto_section(
        sections_with(None), [HAMILTON_F1, GTA_GAME, TSX, calm], TODAY
    )
    assert toronto_links(out) == [calm["link"]] and stats["backfilled"] == 1


def test_lookalikes_cannot_fill_or_lead_toronto_when_no_toronto_candidate_exists():
    out, _ = toronto.enforce_toronto_section(sections_with(None), [HAMILTON_F1, GTA_GAME, TSX], TODAY)
    assert section(out, "toronto")["stories"] == []


def test_backfill_accepts_toronto_hinted_item_but_not_a_canada_national_one():
    hinted = cand("Quiet week at city hall", "https://example.com/hall", hint="toronto")
    national = cand("Quiet week in the Prairies", "https://example.com/prairies", hint="toronto", lane=NATIONAL)
    out, _ = toronto.enforce_toronto_section(sections_with(None), [national, hinted], TODAY)
    assert toronto_links(out) == [hinted["link"]]


@pytest.mark.parametrize("title", [
    "Lewis Hamilton wins Mexican Grand Prix", "Alexander Hamilton musical returns",
    "GTA VI delayed again, Rockstar says", "GTA 6 trailer breaks records", "GTA V sales top 200 million",
    "Union Station evacuated in Denver",
])
def test_keyword_lookalikes_carry_no_toronto_signal(title):
    assert toronto.toronto_signal({"headline": title}) == ""


@pytest.mark.parametrize("title", [
    "Hamilton, Ont., council backs transit plan", "City of Hamilton opens warming centres",
    "Hamilton Spectator reports mill closure", "New GTA hospital funding announced",
    "Toronto's Union Station reopens its east wing",
])
def test_real_hamilton_gta_and_union_station_stories_keep_a_signal(title):
    assert toronto.toronto_signal({"headline": title}) == "headline"


def test_hamilton_newswire_dateline_keeps_a_signal():
    release = cand("Water main upgrade", "https://example.com/wm",
                   description="HAMILTON, ON, Oct. 14, 2026 /CNW/ - Crews begin work downtown.")
    assert toronto.toronto_signal({}, release) == "dateline"


@pytest.mark.parametrize("attrs", [
    {"section_hint": "opinion"}, {"content_genre": "opinion"},
    {"link": "https://example.com/opinions/a"}, {"link": "https://example.com/voices/a"},
    {"link": "https://example.com/leaders/a"},
])
def test_backfill_skips_opinion_by_hint_genre_or_path(attrs):
    base = cand("Why Toronto needs a plan", "https://example.com/plan", source="CBC Toronto", hint="toronto")
    out, _ = toronto.enforce_toronto_section(sections_with(None), [dict(base, **attrs)], TODAY)
    assert toronto_links(out) == []


@pytest.mark.parametrize("title", [
    "Armed robbery at Etobicoke jewellery store", "Carjacking in Brampton", "Home invasion in Vaughan",
    "Kidnapping suspect arrested in Markham", "Man abducted in Scarborough", "Gunman held in Toronto",
    "Gunfire heard near Jane and Finch", "Slain man identified", "Manslaughter charge laid in Toronto",
])
def test_backfill_marks_newly_covered_incidents_sensitive_and_sorts_them_last(title):
    # A civic reason keeps the incident eligible under the crime gate (#71), so
    # this exercises sensitivity ordering rather than the gate's exclusion.
    incident = cand(title, "https://example.com/incident", source="CBC Toronto", hint="toronto",
                    description="Police warn the public; suspect at large.")
    calm = cand("Scarborough library reopens", "https://example.com/c", source="CBC Toronto", hint="toronto")
    out, _ = toronto.enforce_toronto_section(sections_with(None), [incident, calm], TODAY)
    stories = section(out, "toronto")["stories"]
    assert [s["link"] for s in stories] == [calm["link"], incident["link"]]
    assert [s["sensitivity"] for s in stories] == [False, True]


def test_backfilled_cards_carry_a_backfill_marker_and_model_cards_do_not():
    # Two model cards, one of them off-city: the removed slot is backfilled.
    cards = [card(WAYMO, 1), card(MORDEN, 2)]
    out, _ = toronto.enforce_toronto_section(sections_with(cards), [WAYMO, MORDEN, SANTA_FUND], TODAY)
    stories = section(out, "toronto")["stories"]
    assert [s["link"] for s in stories] == [WAYMO["link"], SANTA_FUND["link"]]
    assert [bool(s.get("backfill")) for s in stories] == [False, True]


def test_no_toronto_candidate_at_all_degrades_to_an_empty_section_with_an_error_log(caplog):
    with caplog.at_level(logging.ERROR, logger="the-daily.toronto"):
        out, stats = toronto.enforce_toronto_section(sections_with(None), OFF_CITY, TODAY)
    assert section(out, "toronto")["stories"] == [] and stats["final"] == 0
    assert any("empty" in r.message for r in caplog.records)


def test_off_city_only_toronto_section_without_candidates_publishes_empty():
    out, stats = toronto.enforce_toronto_section(sections_with([card(MORDEN, 1)], world=[]), [MORDEN], TODAY)
    assert section(out, "toronto")["stories"] == [] and stats["final"] == 0


# --- curate hook -------------------------------------------------------------

def test_hook_reelects_lead_and_keeps_caps_after_removals():
    raw = {"sections": sections_with([card(MORDEN, 1, lead=True), card(WAYMO, 2), card(BIKE_LANES, 3)])}
    sections = _normalize_edition(raw)

    out = _guard_toronto_section(sections, [MORDEN, WAYMO, BIKE_LANES, SANTA_FUND], TODAY)

    stories = section(out, "toronto")["stories"]
    assert [s["lead"] for s in stories].count(True) == 1 and stories[0]["lead"] is True
    assert MORDEN["link"] not in [s["link"] for s in stories]
    assert len(stories) == 3  # same size as the model's section; MORDEN replaced from the pool
    assert SANTA_FUND["link"] in [s["link"] for s in stories]
    assert all(s["analysis"] is None for s in stories)


def test_hook_leaves_a_clean_edition_unchanged():
    cards = [card(WAYMO, 1, lead=True), card(SANTA_FUND, 2), card(BIKE_LANES, 3)]
    sections = _normalize_edition({"sections": sections_with(cards, world=[card(MORDEN, 9)])})
    before = [(s["id"], [x["link"] for x in s["stories"]]) for s in sections]

    out = _guard_toronto_section(sections, [WAYMO, SANTA_FUND, BIKE_LANES, MORDEN], TODAY)

    assert [(s["id"], [x["link"] for x in s["stories"]]) for s in out] == before


def test_hook_keeps_an_empty_toronto_tab_when_there_is_no_candidate():
    sections = _normalize_edition({"sections": sections_with(None, world=[card(MORDEN, 1)])})
    out = _guard_toronto_section(sections, [MORDEN], TODAY)
    assert section(out, "toronto") == {"id": "toronto", "label": "Toronto", "stories": []}


def test_canada_national_recall_is_untouched_by_the_guard():
    # The guard runs after curation and never sees the bounded input: the
    # Canada reservation in _trim_input still protects national candidates.
    from src.curate import _trim_input

    stories = [cand(f"Routine {i}", f"https://example.com/r{i}", hint=h)
               for i in range(12) for h in ("world", "business")]
    stories.append(MORDEN)
    assert MORDEN in _trim_input(stories, total=8, today=TODAY)


def test_backfill_never_readds_incidents_withheld_by_the_crime_gate():
    from src import crime

    incident = cand(
        "Man shot dead outside Scarborough restaurant",
        "https://example.com/withheld",
        source="CBC Toronto",
        hint="toronto",
        description="Police are investigating.",
    )
    calm = cand("Scarborough library reopens", "https://example.com/calm", source="CBC Toronto", hint="toronto")
    assert crime.is_unsupported_incident(incident)

    out, _ = toronto.enforce_toronto_section(sections_with(None), [incident, calm], TODAY)

    links = [s["link"] for s in section(out, "toronto")["stories"]]
    assert links == [calm["link"]]
