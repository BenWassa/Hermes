"""Focused browser regression for Champions League compact-table semantics."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from src import render as render_mod

FIXTURE = Path("data/fixtures/edition_sample.json")
ARTIFACTS = Path("test-artifacts")


def _edition() -> dict:
    edition = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if not any(section.get("id") == "sports" for section in edition.get("sections", [])):
        edition["sections"].insert(3, {"id": "sports", "label": "Sports", "stories": []})

    def team(key: str, name: str, league: str) -> dict:
        return {
            "snapshot": {
                "team": {"key": key, "name": name, "league": league, "abbreviation": "TOR"},
                "phase": "preseason",
                "available": True,
                "error": None,
                "source": "fixture",
                "fetched_at": "2026-09-11T12:00:00Z",
                "last_game": None,
                "record": None,
                "standing": None,
                "next_game": None,
            },
            "headline": None,
        }

    edition["sports"] = {
        "version": 1,
        "toronto": [
            team("leafs", "Toronto Maple Leafs", "NHL"),
            team("raptors", "Toronto Raptors", "NBA"),
            team("blue-jays", "Toronto Blue Jays", "MLB"),
        ],
        "major_events": {
            "event_mode": False,
            "max_items": 6,
            "events": [
                {
                    "key": "champions-league",
                    "label": "UEFA Champions League",
                    "priority": 80,
                    "event_mode": False,
                    "available": True,
                    "error": None,
                    "source": "ESPN",
                    "fetched_at": "2026-09-11T12:00:00Z",
                    "matches": [
                        {
                            "id": "ucl-1",
                            "start_time_utc": "2026-09-10T19:00:00Z",
                            "start_time_toronto": "2026-09-10T15:00:00-04:00",
                            "home_team": "Bayern Munich",
                            "away_team": "Bodo/Glimt",
                            "status": "final",
                            "stage": "league-phase",
                            "home_score": 5,
                            "away_score": 0,
                            "detail": "FT",
                            "canada_involved": False,
                        },
                        {
                            "id": "ucl-2",
                            "start_time_utc": "2026-09-10T19:00:00Z",
                            "start_time_toronto": "2026-09-10T15:00:00-04:00",
                            "home_team": "Manchester United",
                            "away_team": "Sabah FK",
                            "status": "final",
                            "stage": "league-phase",
                            "home_score": 4,
                            "away_score": 0,
                            "detail": "FT",
                            "canada_involved": False,
                        },
                    ],
                    "standings": {
                        "label": "League Phase",
                        "rows": [
                            {"position": 1, "team": "Bayern Munich", "played": 1, "points": 3, "goal_difference": 5, "canada": False},
                            {"position": 2, "team": "Manchester United", "played": 1, "points": 3, "goal_difference": 4, "canada": False},
                            {"position": 3, "team": "Como", "played": 1, "points": 3, "goal_difference": 3, "canada": False},
                            {"position": 8, "team": "Barcelona", "played": 1, "points": 3, "goal_difference": 1, "canada": False},
                            {"position": 9, "team": "Arsenal", "played": 1, "points": 3, "goal_difference": 1, "canada": False},
                        ],
                    },
                    "highlights": [],
                }
            ],
        },
        "major_headlines": [],
    }
    return edition


def test_champions_league_compact_table_explains_omissions_and_cut(monkeypatch):
    ARTIFACTS.mkdir(exist_ok=True)
    monkeypatch.setattr(render_mod, "LATEST", ARTIFACTS / "latest-ucl.json")
    output = render_mod.render(_edition(), output_path=ARTIFACTS / "ucl-render.html").resolve()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(output.as_uri())
        page.locator('[data-tab="sports"]').click()
        root = page.locator('[data-sports-event="champions-league"]')
        root.wait_for(state="visible")

        assert page.locator("#sports-toronto-title").inner_text() == "Toronto"
        assert page.locator(".sports-toronto .sports-section-kicker").inner_text() == "Home teams"
        assert page.locator("#sports-events-title").inner_text() == "Major Events"
        assert page.locator(".sports-events .sports-section-kicker").inner_text() == "Global board"

        assert root.locator(".sports-event-stage").inner_text() == "League Phase"
        assert all("League Phase" not in text for text in root.locator(".sports-match-meta").all_inner_texts())

        label = root.locator(".sports-table-label").inner_text()
        assert "League Phase" in label
        assert "qualification cut" in label.lower()
        assert "Positions 4–7 omitted" in root.locator(".sports-table-gap").inner_text()
        assert "Top 8" in root.locator(".sports-table-note").inner_text()
        assert "9–24" in root.locator(".sports-table-note").inner_text()

        positions = root.locator(".sports-table tbody tr:not(.sports-table-gap) td:first-child").all_inner_texts()
        assert positions == ["1", "2", "3", "8", "9"]
        assert root.locator(".sports-qualification-cut").count() == 1

        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert overflow <= 1
        browser.close()
