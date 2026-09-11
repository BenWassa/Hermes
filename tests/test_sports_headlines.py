import datetime as dt

from src.sports.headlines import (
    Significance,
    SportsHeadlineCandidate,
    classify_significance,
    dedupe_and_rank,
    qualify,
    select_team_winners,
    sports_model_payload,
)

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 9, 11, 12, tzinfo=UTC)


def c(title, description="", *, source="The Guardian", hours=1, team=None, url=None):
    slug = str(abs(hash((title, source))))
    return SportsHeadlineCandidate(
        title=title,
        description=description,
        url=url or f"https://example.com/{slug}",
        source=source,
        published_at=NOW - dt.timedelta(hours=hours),
        team_key=team,
    )


def test_major_trade_qualifies():
    item = c("Maple Leafs trade for star defenceman in blockbuster deal")
    assert classify_significance(item) == Significance.MAJOR_TRANSACTION
    assert qualify([item])[0].team_key == "leafs"


def test_material_injury_requires_severity():
    routine = c("Raptors injury update after practice")
    severe = c("Raptors guard to undergo surgery and miss three months")
    assert classify_significance(routine) is None
    assert classify_significance(severe) == Significance.MATERIAL_INJURY


def test_trade_talk_and_could_sign_are_suppressed():
    assert classify_significance(c("Maple Leafs trade talk: five possible targets")) is None
    assert classify_significance(c("Blue Jays could sign veteran starter this winter")) is None


def test_routine_recap_preview_and_quotes_are_suppressed():
    titles = [
        "Blue Jays game recap: Toronto beats Baltimore 5-2",
        "Raptors preview: five things to watch tonight",
        "Maple Leafs postgame quotes after Montreal win",
    ]
    assert all(classify_significance(c(title)) is None for title in titles)


def test_generic_record_word_is_not_a_milestone():
    assert classify_significance(c("Blue Jays improve record to 74-74 after win")) is None
    major = c("Blue Jays star sets franchise record for home runs")
    assert classify_significance(major) == Significance.AWARD_MILESTONE


def test_leadership_retirement_discipline_and_championship_taxonomy():
    cases = {
        "Maple Leafs fire head coach after playoff exit": Significance.LEADERSHIP,
        "Raptors legend announces retirement": Significance.RETIREMENT,
        "Blue Jays pitcher suspended 20 games": Significance.DISCIPLINE,
        "Raptors clinch a playoff berth with late win": Significance.CHAMPIONSHIP,
    }
    for title, expected in cases.items():
        assert classify_significance(c(title)) == expected


def test_max_one_winner_per_team_prefers_higher_significance():
    items = [
        c("Maple Leafs sign forward to three-year contract", hours=1),
        c("Maple Leafs fire head coach after review", hours=4),
        c("Raptors star to undergo surgery and miss two months", hours=2),
    ]
    winners = select_team_winners(items, now=NOW)
    assert set(winners) == {"leafs", "raptors"}
    assert winners["leafs"].significance == Significance.LEADERSHIP


def test_cross_source_duplicate_collapses_and_corroboration_boosts():
    a = c(
        "Blue Jays trade for ace starter in blockbuster deal",
        source="Reuters",
        url="https://reuters.com/a?utm_source=x",
    )
    b = c(
        "Blue Jays trade for ace starter in blockbuster deal",
        source="The Guardian",
        url="https://theguardian.com/b",
    )
    ranked = dedupe_and_rank(qualify([a, b]), now=NOW)
    assert len(ranked) == 1
    assert ranked[0].corroboration == 2
    assert ranked[0].candidate.source == "Reuters"


def test_tracking_variants_of_same_url_collapse():
    a = c(
        "Raptors hire new head coach",
        source="The Guardian",
        url="https://example.com/story?utm_source=feed",
    )
    b = c(
        "Raptors hire new head coach",
        source="The Guardian",
        url="https://www.example.com/story?utm_medium=social",
    )
    assert len(dedupe_and_rank(qualify([a, b]), now=NOW)) == 1


def test_cricket_never_leaks_even_with_team_wording():
    item = c("Toronto Raptors owner backs new cricket league after team sale")
    assert qualify([item]) == []


def test_offseason_major_update_survives_without_team_state_dependency():
    item = c("Blue Jays sign ace pitcher to six-year contract", hours=2)
    winners = select_team_winners([item], now=NOW)
    assert winners["blue-jays"].significance == Significance.MAJOR_TRANSACTION


def test_empty_day_has_no_filler_and_zero_model_payload():
    routine = [
        c("Maple Leafs practice notes and line combinations"),
        c("Raptors preview tonight's preseason game"),
        c("Blue Jays takeaways from yesterday's loss"),
    ]
    winners = select_team_winners(routine, now=NOW)
    assert winners == {}
    assert sports_model_payload(winners) == []


def test_selected_winners_still_add_zero_gemini_payload():
    winners = select_team_winners(
        [c("Raptors star to undergo surgery and miss three months")],
        now=NOW,
    )
    assert "raptors" in winners
    assert sports_model_payload(winners) == []


def test_team_alias_matching_is_bounded_not_generic_toronto():
    item = c("Toronto soccer club fires head coach")
    assert qualify([item]) == []


def test_source_authority_breaks_equal_significance_tie():
    guardian = c(
        "Maple Leafs sign star winger to five-year contract",
        source="The Guardian",
        hours=1,
        url="https://guardian.example/a",
    )
    reuters = c(
        "Maple Leafs sign star winger to five-year contract",
        source="Reuters",
        hours=3,
        url="https://reuters.example/b",
    )
    ranked = dedupe_and_rank(qualify([guardian, reuters]), now=NOW)
    assert ranked[0].candidate.source == "Reuters"
