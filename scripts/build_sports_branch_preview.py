"""Temporary #39 live Sports preview builder.

Builds current Sports V2 from live providers and renders it into a branch-only
HTML file using the normal Hermes template. It deliberately does not call
Gemini or overwrite docs/index.html. Remove with the preview workflow before
#39 merges.

The branch preview currently includes an explicit visual experiment using
remote, official/league-hosted Toronto team marks plus ESPN-hosted Champions
League club crests. Those marks are not copied into the repository and this
experiment is not production authority.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from src import config
from src import render as render_mod
from src.sports import build_sports_desk

TORONTO = ZoneInfo("America/Toronto")
FIXTURE = Path("data/fixtures/edition_sample.json")
OUTPUT = Path("docs/sports-preview.html")
CACHE = Path("data/sports-preview-edition.json")
METRICS = Path("data/sports-preview-metrics.json")

_ESPN_UCL_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard"
_ESPN_UCL_STANDINGS = "https://site.api.espn.com/apis/v2/sports/soccer/uefa.champions/standings"
_TIMEOUT = 15

_MARK_CSS = r"""
/* Branch-only experiment: official-hosted marks in normalized optical boxes. */
.sports-team::before { display: none !important; }
.sports-team { padding-left: 54px !important; }
.sports-preview-mark {
  position: absolute;
  left: 0;
  top: 13px;
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  overflow: visible;
}
.sports-preview-mark img,
.sports-preview-mark picture {
  display: block;
  width: 100%;
  height: 100%;
}
.sports-preview-mark img {
  object-fit: contain;
  object-position: center;
}
.sports-preview-mark-fallback {
  display: none;
  width: 32px;
  min-height: 31px;
  padding: 4px 0 3px;
  border-top: 2px solid var(--navy);
  border-bottom: 1px solid var(--navy);
  font-family: 'Georgia', serif;
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: -0.04em;
  text-align: center;
  color: var(--navy-ink);
}
.sports-preview-mark.failed .sports-preview-mark-fallback { display: block; }
.sports-preview-mark.failed img,
.sports-preview-mark.failed picture { display: none; }

/* Champions League crests stay subordinate to the scoreline. 24px is enough
   to identify a club without turning the digest into a scores app. */
.sports-preview-club {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.sports-preview-club-crest {
  width: 24px;
  height: 24px;
  flex: 0 0 24px;
  object-fit: contain;
  object-position: center;
  vertical-align: middle;
}
.sports-table-team-preview {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.sports-table-team-preview .sports-preview-club-crest {
  width: 20px;
  height: 20px;
  flex-basis: 20px;
}
@media (max-width: 380px) {
  .sports-team { padding-left: 48px !important; }
  .sports-preview-mark { width: 36px; height: 36px; top: 14px; }
  .sports-preview-club { gap: 5px; }
  .sports-preview-club-crest { width: 21px; height: 21px; flex-basis: 21px; }
  .sports-table-team-preview .sports-preview-club-crest { width: 18px; height: 18px; flex-basis: 18px; }
}
"""

_MARK_JS = r"""
(function () {
  var MARKS = {
    'leafs': {
      light: 'https://assets.nhle.com/logos/nhl/svg/TOR_light.svg',
      dark: 'https://assets.nhle.com/logos/nhl/svg/TOR_dark.svg',
      fallback: 'ML'
    },
    'raptors': {
      light: 'https://cdn.nba.com/logos/nba/1610612761/primary/L/logo.svg',
      fallback: 'R'
    },
    'blue-jays': {
      light: 'https://www.mlbstatic.com/team-logos/141.svg',
      fallback: 'BJ'
    }
  };

  var editionNode = document.getElementById('edition');
  var sports = null;
  try { sports = JSON.parse(editionNode.textContent).sports; } catch (e) {}

  function markHtml(key, mark) {
    var image;
    if (mark.dark) {
      image = '<picture><source media="(prefers-color-scheme: dark)" srcset="' + mark.dark + '">' +
        '<img src="' + mark.light + '" alt="" aria-hidden="true" referrerpolicy="no-referrer" decoding="async"></picture>';
    } else {
      image = '<img src="' + mark.light + '" alt="" aria-hidden="true" referrerpolicy="no-referrer" decoding="async">';
    }
    return '<span class="sports-preview-mark" data-preview-mark="' + key + '" aria-hidden="true">' +
      image + '<span class="sports-preview-mark-fallback">' + mark.fallback + '</span></span>';
  }

  function wire(markNode) {
    var img = markNode.querySelector('img');
    if (!img) { markNode.classList.add('failed'); return; }
    function fail() { markNode.classList.add('failed'); }
    function ok() { markNode.classList.remove('failed'); }
    img.addEventListener('error', fail, { once: true });
    img.addEventListener('load', ok, { once: true });
    if (img.complete) {
      if (img.naturalWidth > 0) ok(); else fail();
    }
  }

  function addClubCrest(node, url, tableMode) {
    if (!node || !url || node.querySelector('.sports-preview-club-crest')) return;
    var img = document.createElement('img');
    img.className = 'sports-preview-club-crest';
    img.src = url;
    img.alt = '';
    img.setAttribute('aria-hidden', 'true');
    img.setAttribute('decoding', 'async');
    img.setAttribute('loading', 'lazy');
    img.setAttribute('referrerpolicy', 'no-referrer');
    img.addEventListener('error', function () { img.remove(); }, { once: true });
    node.insertBefore(img, node.firstChild);
    node.classList.add(tableMode ? 'sports-table-team-preview' : 'sports-preview-club');
  }

  function championsPayload() {
    var events = sports && sports.major_events && sports.major_events.events;
    if (!events) return null;
    return events.find(function (event) { return event.key === 'champions-league'; }) || null;
  }

  function decorateChampions() {
    var event = championsPayload();
    if (!event) return;
    var root = document.querySelector('[data-sports-event="champions-league"]');
    if (!root) return;

    var matchRows = root.querySelectorAll('.sports-match');
    (event.matches || []).forEach(function (match, index) {
      var row = matchRows[index];
      if (!row) return;
      var clubs = row.querySelectorAll('.sports-match-teams > span:not([aria-hidden])');
      if (clubs[0]) addClubCrest(clubs[0], match.home_logo_url, false);
      if (clubs[1]) addClubCrest(clubs[1], match.away_logo_url, false);
    });

    var tableRows = root.querySelectorAll('.sports-table tbody tr');
    var standings = event.standings && event.standings.rows;
    (standings || []).forEach(function (rowData, index) {
      var row = tableRows[index];
      if (!row || !row.cells || row.cells.length < 2) return;
      addClubCrest(row.cells[1], rowData.logo_url, true);
    });
  }

  function decorateToronto() {
    Object.keys(MARKS).forEach(function (key) {
      var team = document.querySelector('[data-sports-team="' + key + '"]');
      if (!team || team.querySelector('[data-preview-mark]')) return;
      team.insertAdjacentHTML('afterbegin', markHtml(key, MARKS[key]));
      wire(team.querySelector('[data-preview-mark]'));
    });
  }

  function decorate() {
    decorateToronto();
    decorateChampions();
  }

  var stories = document.getElementById('stories');
  if (stories && window.MutationObserver) {
    new MutationObserver(decorate).observe(stories, { childList: true, subtree: true });
  }
  var tab = document.querySelector('[data-tab="sports"]');
  if (tab) tab.addEventListener('click', function () { window.setTimeout(decorate, 0); });
  decorate();
})();
"""


def _navigation_shell(edition: dict) -> list[dict]:
    existing = {
        section.get("id"): section
        for section in edition.get("sections", [])
        if section.get("id") != "sports"
    }
    sections: list[dict] = []
    for spec in config.SECTIONS:
        if spec["id"] == "sports":
            sections.append({"id": "sports", "label": "Sports", "stories": []})
            continue
        section = existing.get(spec["id"])
        if section:
            sections.append(section)
    return sections


def _espn_team_logo(team: dict) -> str | None:
    direct = team.get("logo")
    if isinstance(direct, str) and direct.startswith("https://"):
        return direct
    for item in team.get("logos") or []:
        href = item.get("href") if isinstance(item, dict) else None
        if isinstance(href, str) and href.startswith("https://"):
            return href
    team_id = str(team.get("id") or "").strip()
    if team_id:
        return f"https://a.espncdn.com/i/teamlogos/soccer/500/{team_id}.png"
    return None


def _team_name(team: dict) -> str:
    return str(team.get("displayName") or team.get("name") or team.get("shortDisplayName") or "").strip()


def _attach_champions_logo_preview(payload: dict, *, now: dt.datetime) -> int:
    """Preserve ESPN crest URLs in the branch-only rendered payload.

    Sports V2 intentionally normalizes away provider presentation fields. This
    preview makes two extra bounded requests solely to test the visual treatment
    before deciding whether crest identity belongs in the production contract.
    """
    events = ((payload.get("major_events") or {}).get("events") or [])
    snapshot = next((item for item in events if item.get("key") == "champions-league"), None)
    if not snapshot:
        return 0

    local_date = now.astimezone(TORONTO).date()
    dates = f"{local_date - dt.timedelta(days=1):%Y%m%d}-{local_date + dt.timedelta(days=7):%Y%m%d}"
    attached = 0
    logos_by_name: dict[str, str] = {}

    try:
        response = requests.get(_ESPN_UCL_SCOREBOARD, params={"dates": dates}, timeout=_TIMEOUT)
        response.raise_for_status()
        raw_events = response.json().get("events") or []
        raw_by_id = {str(item.get("id") or ""): item for item in raw_events}

        for match in snapshot.get("matches") or []:
            raw = raw_by_id.get(str(match.get("id") or "")) or {}
            competitions = raw.get("competitions") or []
            competitors = (competitions[0] or {}).get("competitors") or [] if competitions else []
            home = next((item for item in competitors if item.get("homeAway") == "home"), None)
            away = next((item for item in competitors if item.get("homeAway") == "away"), None)
            for side, competitor in (("home", home), ("away", away)):
                if not competitor:
                    continue
                team = competitor.get("team") or {}
                logo = _espn_team_logo(team)
                name = _team_name(team)
                if name and logo:
                    logos_by_name[name.casefold()] = logo
                if logo:
                    match[f"{side}_logo_url"] = logo
                    attached += 1
    except Exception:
        pass

    try:
        response = requests.get(_ESPN_UCL_STANDINGS, timeout=_TIMEOUT)
        response.raise_for_status()
        for group in response.json().get("children") or []:
            for entry in ((group.get("standings") or {}).get("entries") or []):
                team = entry.get("team") or {}
                name = _team_name(team)
                logo = _espn_team_logo(team)
                if name and logo:
                    logos_by_name[name.casefold()] = logo
    except Exception:
        pass

    standings = snapshot.get("standings") or {}
    for row in standings.get("rows") or []:
        logo = logos_by_name.get(str(row.get("team") or "").casefold())
        if logo:
            row["logo_url"] = logo
            attached += 1

    return attached


def _inject_preview_marks(path: Path) -> None:
    html = path.read_text(encoding="utf-8")
    if "</style>" not in html or "</body>" not in html:
        raise ValueError("preview HTML is missing mark injection anchors")
    html = html.replace("</style>", _MARK_CSS + "\n</style>", 1)
    html = html.replace("</body>", "<script>\n" + _MARK_JS + "\n</script>\n</body>", 1)
    path.write_text(html, encoding="utf-8")


def main() -> None:
    now = dt.datetime.now(dt.timezone.utc)
    local = now.astimezone(TORONTO)

    edition = json.loads(FIXTURE.read_text(encoding="utf-8"))
    edition["date"] = local.strftime("%A, %B %-d, %Y")
    edition["sections"] = _navigation_shell(edition)

    sports = build_sports_desk(now=now)
    edition["sports"] = sports.payload
    champions_marks = _attach_champions_logo_preview(edition["sports"], now=now)

    render_mod.LATEST = CACHE
    out = render_mod.render(edition, output_path=OUTPUT)
    _inject_preview_marks(out)
    METRICS.write_text(
        json.dumps(
            {
                "built_at": now.isoformat().replace("+00:00", "Z"),
                "toronto_date": local.date().isoformat(),
                "official_mark_preview": True,
                "champions_crest_preview_count": champions_marks,
                **sports.metrics,
            },
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    print(f"Sports preview: {out}")
    print(f"CHAMPIONS_PREVIEW_CRESTS={champions_marks}")
    print("SPORTS_PREVIEW_METRICS=" + json.dumps(sports.metrics, sort_keys=True))


if __name__ == "__main__":
    main()
