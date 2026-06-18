"""Task 7 - Orchestrator.

Single entrypoint chaining the whole pipeline:

    weather -> fetch -> normalize -> curate -> resolve_images -> render

Each stage failure is logged with its stage name and exits non-zero so CI
surfaces it. A one-line summary prints at the end.
"""

from __future__ import annotations

import logging
import sys

from . import weather as weather_mod
from .curate import curate
from .fetch import fetch_all
from .images import resolve_images
from .normalize import normalize
from .render import render

log = logging.getLogger("the-daily.build")


def main() -> int:
    stage = "start"
    try:
        stage = "weather"
        weather = weather_mod.get_weather()

        stage = "fetch"
        raw = fetch_all()

        stage = "normalize"
        stories = normalize(raw)
        log.info("normalized %d stories", len(stories))
        if not stories:
            raise RuntimeError("no stories fetched; aborting before curation")

        stage = "curate"
        edition = curate(stories, weather=weather)

        stage = "images"
        resolve_images(edition)

        stage = "render"
        out = render(edition)
    except Exception as exc:  # noqa: BLE001 - top-level guard for CI visibility
        log.error("build failed at stage '%s': %s", stage, exc)
        return 1

    sections = edition["sections"]
    all_stories = [st for s in sections for st in s["stories"]]
    shown = sum(1 for st in all_stories if st.get("image"))
    suppressed = len(all_stories) - shown
    log.info(
        "edition '%s' -> %s | sections=%d stories=%d images shown=%d suppressed=%d",
        edition.get("date", "?"), out, len(sections), len(all_stories), shown, suppressed,
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.exit(main())
