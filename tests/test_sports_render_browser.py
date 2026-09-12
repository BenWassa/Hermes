"""Rendered-browser acceptance for the Sports V2 broadsheet treatment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src import render as render_mod

ARTIFACTS = Path("test-artifacts")
FIXTURE = Path("data/fixtures/edition_sample.json")


def _game(identifier, opponent, when, *, status="scheduled", result=None, team_score=None, opponent_score=None, home_away="home"):
    return {
        "id": identifier,
        "start_time_utc": when,
        "start_time_toronto": when,
        "opponent": opponent,
        "opponent_abbreviation": opponent[:3].upper(),
        "home_away": home_away,
        "status": status,
        "phase": "regular",
        "team_score": team_score,
        "opponent_score": opponent_score,
        "result": result,
    }


def _team(key, name, league, phase, *, available=True, last=None, record=None, standing=None, next_game=None):
    return {
        "snapshot": {
            "team": {"key": key, "name": name, "league": league, "abbreviation": "TOR"},
            "phase": phase,
            "available": available,
            "error": None if available else "source_unavailable",
            "source": "fixture",
            "fetched_at": "2026-09-11T10:00:00Z",
            "last_game": last,
            "record": record,
            "standing": standing,
            "next_game": next_game,
        },
        "headline": None,
    }


def _edition() -> dict:
    edition = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert any(section["id"] == "sports" for section in edition["sections"])

    leafs = _team(
        "leafs",
        "Toronto Maple Leafs",
        "NHL",
        "postseason",
        last=_game(
            "leafs-last", "Boston Bruins", "2026-09-10T23:00:00Z", status="final",
            result="W", team_score=4, opponent_score=2,
        ),
        record={"wins": 52, "losses": 24, "overtime_losses": 6, "display": "52–24–6"},
        standing={"label": "2nd Atlantic · four points back", "rank": 2, "scope": "Atlantic", "games_back": None},
        next_game=_game("leafs-next", "Montréal Canadiens", "2026-09-13T00:00:00Z", home_away="away"),
    )
    leafs["headline"] = {
        "team_key": "leafs",
        "significance": "material_injury",
        "headline": "Leafs lose a top-line forward for the rest of the series",
        "description": "The injury changes Toronto's deployment before Game 5.",
        "url": "https://example.com/leafs-major-update",
        "source": "The Guardian",
        "published_at": "2026-09-11T08:00:00Z",
        "corroboration": 2,
    }

    raptors = _team(
        "raptors", "Toronto Raptors", "NBA", "regular", available=False,
    )
    jays = _team(
        "blue-jays", "Toronto Blue Jays", "MLB", "offseason",
        next_game=_game(
            "jays-next", "New York Yankees", "2027-03-28T17:07:00Z", home_away="home"
        ),
    )

    edition["sports"] = {
        "version": 1,
        "toronto": [leafs, raptors, jays],
        "major_events": {
            "event_mode": True,
            "max_items": 12,
            "events": [
                {
                    "key": "fifa-world-cup-2030",
                    "label": "FIFA World Cup",
                    "priority": 100,
                    "event_mode": True,
                    "available": True,
                    "error": None,
                    "source": "ESPN",
                    "fetched_at": "2030-06-20T10:00:00Z",
                    "matches": [
                        {
                            "id": "wc-canada",
                            "start_time_utc": "2030-06-20T18:00:00Z",
                            "start_time_toronto": "2030-06-20T14:00:00-04:00",
                            "home_team": "Canada",
                            "away_team": "Spain",
                            "status": "scheduled",
                            "stage": "group-stage",
                            "home_score": None,
                            "away_score": None,
                            "detail": "Group B",
                            "canada_involved": True,
                        },
                        {
                            "id": "wc-final",
                            "start_time_utc": "2030-06-19T20:00:00Z",
                            "start_time_toronto": "2030-06-19T16:00:00-04:00",
                            "home_team": "Brazil",
                            "away_team": "France",
                            "status": "final",
                            "stage": "round-of-16",
                            "home_score": 2,
                            "away_score": 1,
                            "detail": "FT",
                            "canada_involved": False,
                        },
                    ],
                    "standings": {
                        "label": "Group B",
                        "rows": [
                            {"position": 1, "team": "Canada", "played": 2, "points": 6, "goal_difference": 3, "canada": True},
                            {"position": 2, "team": "Spain", "played": 2, "points": 3, "goal_difference": 1, "canada": False},
                            {"position": 3, "team": "Ghana", "played": 2, "points": 1, "goal_difference": -1, "canada": False},
                            {"position": 4, "team": "Chile", "played": 2, "points": 1, "goal_difference": -3, "canada": False},
                        ],
                    },
                    "highlights": [],
                }
            ],
        },
        "major_headlines": [
            {
                "event_key": "nfl-postseason",
                "headline": "Conference championship produces a major upset",
                "description": "The result resets the Super Bowl matchup.",
                "url": "https://example.com/nfl-upset",
                "source": "The Guardian",
                "published_at": "2026-09-11T07:00:00Z",
            }
        ],
    }
    return edition


def _render(monkeypatch: pytest.MonkeyPatch) -> Path:
    ARTIFACTS.mkdir(exist_ok=True)
    monkeypatch.setattr(render_mod, "LATEST", ARTIFACTS / "latest-sports-edition.json")
    return render_mod.render(_edition(), output_path=ARTIFACTS / "sports-edition.html").resolve()


def _open_sports(page) -> None:
    page.locator('[data-tab="sports"]').click()
    page.locator("#sports-toronto-title").wait_for(state="visible")
    assert page.locator("#stories").get_attribute("data-sports-rendered") == "true"


@pytest.mark.parametrize(
    "width,height,color_scheme",
    [
        (412, 915, "light"),
        (390, 844, "light"),
        (320, 568, "light"),
        (844, 390, "light"),
        (390, 844, "dark"),
    ],
)
def test_sports_is_broadsheet_ordered_and_responsive(
    monkeypatch: pytest.MonkeyPatch, width: int, height: int, color_scheme: str
):
    artifact = _render(monkeypatch)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": width, "height": height},
            has_touch=True,
            is_mobile=True,
            color_scheme=color_scheme,
        )
        page = context.new_page()
        page.goto(artifact.as_uri())
        _open_sports(page)

        teams = page.locator("[data-sports-team]").evaluate_all(
            "els => els.map(el => el.getAttribute('data-sports-team'))"
        )
        assert teams == ["leafs", "raptors", "blue-jays"]
        assert page.locator(".sports-toronto .card").count() == 0
        assert page.locator(".sports-toronto img").count() == 0
        assert page.locator('[data-sports-team="leafs"] .sports-score').inner_text() == "4–2"
        assert "52–24–6" in page.locator('[data-sports-team="leafs"]').inner_text()
        assert "Montréal Canadiens" in page.locator('[data-sports-team="leafs"]').inner_text()
        assert page.locator('[data-sports-team="raptors"] .sports-status-line strong').text_content() == "Unavailable"
        assert page.locator('[data-sports-team="blue-jays"] .sports-status-line strong').text_content() == "Offseason"
        assert page.locator('[data-sports-team="blue-jays"] .sports-scoreline').count() == 0
        assert page.locator("#sports-events-title").is_visible()
        assert page.locator('[data-sports-event="fifa-world-cup-2030"]').is_visible()
        # Lower event desks may be skipped by content-visibility until scrolled;
        # verify authored DOM content without forcing below-fold layout/paint.
        assert "Canada" in (page.locator(".sports-table tr.canada").text_content() or "")
        assert page.locator("#sports-headlines-title").is_visible()

        overflow = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        assert overflow <= 1

        headline_box = page.locator('[data-sports-team="leafs"] .sports-team-story').bounding_box()
        assert headline_box is not None
        assert headline_box["height"] >= 44

        if color_scheme == "dark":
            paper = page.locator("#app").evaluate("el => getComputedStyle(el).backgroundColor")
            assert paper == "rgb(21, 26, 34)"

        page.screenshot(path=str(ARTIFACTS / f"sports-{width}x{height}-{color_scheme}.png"))
        browser.close()


def test_large_text_and_long_labels_do_not_create_horizontal_overflow(monkeypatch: pytest.MonkeyPatch):
    artifact = _render(monkeypatch)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 320, "height": 568})
        page.goto(artifact.as_uri())
        page.add_style_tag(content="html { font-size: 125% !important; }")
        _open_sports(page)

        overflow = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        assert overflow <= 1
        assert page.locator('[data-sports-team="leafs"]').is_visible()
        assert page.locator(".sports-table").is_visible()
        browser.close()


def test_no_sports_payload_preserves_legacy_renderer_without_sports_assets(monkeypatch: pytest.MonkeyPatch):
    edition = json.loads(FIXTURE.read_text(encoding="utf-8"))
    ARTIFACTS.mkdir(exist_ok=True)
    monkeypatch.setattr(render_mod, "LATEST", ARTIFACTS / "latest-no-sports.json")
    output = render_mod.render(edition, output_path=ARTIFACTS / "no-sports-edition.html")
    html = output.read_text(encoding="utf-8")
    assert "data-sports-rendered" not in html
    assert "Sports V2: newspaper furniture" not in html
