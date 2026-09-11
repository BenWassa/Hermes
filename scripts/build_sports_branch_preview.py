"""Temporary #39 live Sports preview builder.

Builds current Sports V2 from live providers and renders it into a branch-only
HTML file using the normal Hermes template. It deliberately does not call
Gemini or overwrite docs/index.html. Remove with the preview workflow before
#39 merges.

The branch preview currently includes an explicit visual experiment using
remote, official-hosted Toronto team SVG marks. Those marks are not copied into
the repository and this experiment is not production authority.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from src import config
from src import render as render_mod
from src.sports import build_sports_desk

TORONTO = ZoneInfo("America/Toronto")
FIXTURE = Path("data/fixtures/edition_sample.json")
OUTPUT = Path("docs/sports-preview.html")
CACHE = Path("data/sports-preview-edition.json")
METRICS = Path("data/sports-preview-metrics.json")

_MARK_CSS = r"""
/* Branch-only experiment: official-hosted team marks in one optical box. */
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
@media (max-width: 380px) {
  .sports-team { padding-left: 48px !important; }
  .sports-preview-mark { width: 36px; height: 36px; top: 14px; }
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

  function decorate() {
    Object.keys(MARKS).forEach(function (key) {
      var team = document.querySelector('[data-sports-team="' + key + '"]');
      if (!team || team.querySelector('[data-preview-mark]')) return;
      team.insertAdjacentHTML('afterbegin', markHtml(key, MARKS[key]));
      wire(team.querySelector('[data-preview-mark]'));
    });
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

    render_mod.LATEST = CACHE
    out = render_mod.render(edition, output_path=OUTPUT)
    _inject_preview_marks(out)
    METRICS.write_text(
        json.dumps(
            {
                "built_at": now.isoformat().replace("+00:00", "Z"),
                "toronto_date": local.date().isoformat(),
                "official_mark_preview": True,
                **sports.metrics,
            },
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    print(f"Sports preview: {out}")
    print("SPORTS_PREVIEW_METRICS=" + json.dumps(sports.metrics, sort_keys=True))


if __name__ == "__main__":
    main()
