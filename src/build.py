"""Task 7 - Orchestrator.

Single entrypoint chaining the whole pipeline:

    weather -> fetch -> normalize -> voices -> curate -> resolve_images -> render

Voice discovery and Following selection happen before Gemini curation.  The
selected followed set is therefore an input to curation, not a ranking result
that the editor model can silently discard.

Each stage failure is logged with its stage name and exits non-zero so CI
surfaces it. Individual Voice-source failures are already isolated inside the
Voice discovery layer and do not fail the edition.
"""

from __future__ import annotations

import logging
import sys

from . import config
from . import weather as weather_mod
from .curate import curate
from .fetch import fetch_all
from .images import resolve_images
from .normalize import normalize
from .opinion import editorial_without_following, following_seeds
from .render import render
from .voices import discover, load_registry, select_following

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

        stage = "voices"
        registry = load_registry(config.VOICES_REGISTRY_PATH)
        discovery = discover(registry, pool=stories)
        followed = select_following(
            discovery.fresh,
            cap=config.VOICE_FOLLOWING_CAP,
            per_voice=config.VOICE_MAX_PER_VOICE,
        )
        following = following_seeds(followed, registry)
        editorial_stories = editorial_without_following(stories, following)
        log.info(
            "following: %d qualifying, %d selected, %d ordinary Opinion duplicate(s) withheld",
            len(discovery.fresh),
            len(following),
            len(stories) - len(editorial_stories),
        )

        stage = "curate"
        edition = curate(editorial_stories, weather=weather, following=following)

        stage = "images"
        resolve_images(edition)

        stage = "render"
        out = render(edition)
    except Exception as exc:  # noqa: BLE001 - top-level guard for CI visibility
        log.error("build failed at stage '%s': %s", stage, exc)
        return 1

    sections = edition["sections"]
    all_stories = [st for s in sections for st in s["stories"]] + list(edition.get("following", []))
    shown = sum(1 for st in all_stories if st.get("image"))
    suppressed = len(all_stories) - shown
    log.info(
        "edition '%s' -> %s | sections=%d stories=%d following=%d images shown=%d suppressed=%d",
        edition.get("date", "?"),
        out,
        len(sections),
        len(all_stories),
        len(edition.get("following", [])),
        shown,
        suppressed,
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.exit(main())
