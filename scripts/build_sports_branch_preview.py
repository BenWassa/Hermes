"""Temporary #39 live Sports preview builder.

Builds current Sports V2 from live providers and renders it into a branch-only
HTML file using the normal Hermes template. It deliberately does not call
Gemini or overwrite docs/index.html. Remove with the preview workflow before
#39 merges.
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
    METRICS.write_text(
        json.dumps(
            {
                "built_at": now.isoformat().replace("+00:00", "Z"),
                "toronto_date": local.date().isoformat(),
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
