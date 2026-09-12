import datetime as dt
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from src import render as render_mod
from src.sports.espn_events import parse_scoreboard, parse_standings
from src.sports.events import EVENT_REGISTRY
from src.sports.identity import trusted_asset_url

UTC = dt.timezone.utc
FIXTURE = Path("data/fixtures/edition_sample.json")
ARTIFACTS = Path("test-artifacts")


def _spec(key):
    return next(item for item in EVENT_REGISTRY if item.key == key)


def test_trusted_asset_url_requires_https_and_allowlisted_host():
    assert trusted_asset_url("https://a.espncdn.com/i/teamlogos/soccer/500/1.png")
    assert trusted_asset_url("https://assets.nhle.com/logos/nhl/svg/TOR_light.svg")
    assert trusted_asset_url("http://a.espncdn.com/i/teamlogos/soccer/500/1.png") is None
    assert trusted_asset_url("https://evil.example/logo.svg") is None
    assert trusted_asset_url("javascript:alert(1)") is None


def test_espn_identity_is_extracted_from_existing_scoreboard_and_standings_payloads():
    scoreboard = {
        "events": [{
            "id": "ucl-1",
            "date": "2026-09-11T20:00:00Z",
            "season": {"slug": "league-phase"},
            "status": {"type": {"name": "STATUS_FINAL", "state": "post", "completed": True}},
            "competitions": [{"competitors": [
                {"homeAway": "home", "score": "2", "team": {"id": "359", "displayName": "Arsenal", "logo": "https://a.espncdn.com/i/teamlogos/soccer/500/359.png"}},
                {"homeAway": "away", "score": "1", "team": {"id": "83", "displayName": "Barcelona", "logo": "https://evil.example/barca.svg"}},
            ]}],
        }]
    }
    match = parse_scoreboard(scoreboard)[0]
    assert match.home_logo_url == "https://a.espncdn.com/i/teamlogos/soccer/500/359.png"
    # Untrusted direct URL is rejected, but the known ESPN team id provides the
    # deterministic trusted CDN fallback without another network request.
    assert match.away_logo_url == "https://a.espncdn.com/i/teamlogos/soccer/500/83.png"

    entries = []
    for index in range(1, 10):
        entries.append({
            "team": {"id": str(index), "displayName": f"Team {index}", "abbreviation": f"T{index}"},
            "stats": [
                {"name": "gamesPlayed", "value": 1},
                {"name": "points", "value": 3},
                {"name": "pointDifferential", "value": 1},
            ],
        })
    table = parse_standings({"children": [{"name": "League Phase", "standings": {"entries": entries}}]}, spec=_spec("champions-league"))
    assert table is not None
    assert [row.position for row in table.rows] == [1, 2, 3, 8, 9]
    assert all(row.logo_url and row.logo_url.startswith("https://a.espncdn.com/") for row in table.rows)


def test_remote_marks_do_not_enter_dom_before_sports_activation_and_reserve_geometry(monkeypatch):
    edition = json.loads(FIXTURE.read_text(encoding="utf-8"))
    edition["sports"] = {
        "version": 2,
        "toronto": [
            {"snapshot": {"team": {"key": "leafs", "name": "Toronto Maple Leafs", "league": "NHL"}, "phase": "offseason", "available": True, "error": None, "source": "fixture", "fetched_at": "2026-09-11T10:00:00Z", "last_game": None, "record": None, "standing": None, "next_game": None}, "headline": None, "mark": {"light": "https://assets.nhle.com/logos/nhl/svg/TOR_light.svg", "dark": "https://assets.nhle.com/logos/nhl/svg/TOR_dark.svg", "fallback": "ML"}},
            {"snapshot": {"team": {"key": "raptors", "name": "Toronto Raptors", "league": "NBA"}, "phase": "offseason", "available": True, "error": None, "source": "fixture", "fetched_at": "2026-09-11T10:00:00Z", "last_game": None, "record": None, "standing": None, "next_game": None}, "headline": None, "mark": {"light": "https://cdn.nba.com/logos/nba/1610612761/primary/L/logo.svg", "fallback": "R"}},
            {"snapshot": {"team": {"key": "blue-jays", "name": "Toronto Blue Jays", "league": "MLB"}, "phase": "offseason", "available": True, "error": None, "source": "fixture", "fetched_at": "2026-09-11T10:00:00Z", "last_game": None, "record": None, "standing": None, "next_game": None}, "headline": None, "mark": {"light": "https://www.mlbstatic.com/team-logos/141.svg", "fallback": "BJ"}},
        ],
        "major_events": {"event_mode": False, "max_items": 6, "events": []},
        "major_headlines": [],
    }
    ARTIFACTS.mkdir(exist_ok=True)
    monkeypatch.setattr(render_mod, "LATEST", ARTIFACTS / "latest-identity.json")
    output = render_mod.render(edition, output_path=ARTIFACTS / "sports-identity.html").resolve()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        requested = []
        page.route("https://**/*", lambda route: (requested.append(route.request.url), route.abort()))
        page.goto(output.as_uri())
        assert page.locator("[data-sports-mark]").count() == 0
        assert requested == []

        page.locator('[data-tab="sports"]').click()
        page.locator("[data-sports-mark]").first.wait_for(state="attached")
        assert page.locator(".sports-toronto [data-sports-mark]").count() == 3
        first = page.locator(".sports-toronto [data-sports-mark]").first
        box = first.bounding_box()
        assert box is not None
        assert box["width"] == 48
        assert box["height"] == 48
        assert first.locator("img").get_attribute("width") == "48"
        assert first.locator("img").get_attribute("height") == "48"
        assert first.locator("img").get_attribute("decoding") == "async"
        browser.close()


def test_service_worker_does_not_cache_cross_origin_provider_assets():
    sw = Path("docs/sw.js").read_text(encoding="utf-8")
    assert "if (!sameOrigin)" in sw
    assert "e.respondWith(fetch(request))" in sw
    assert "the-daily-v2" in sw
