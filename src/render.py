"""Task 6 - Render.

Inject the edition JSON into the static HTML template and write docs/index.html
(served by GitHub Pages) plus data/latest.json (debug/cache). A build-timestamp
meta tag acts as a cache-buster so phones never show a stale edition.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

TEMPLATE = Path("template/index.template.html")
SPORTS_CSS = Path("template/sports.css")
SPORTS_PERFORMANCE_CSS = Path("template/sports-performance.css")
SPORTS_JS = Path("template/sports.js")
OUTPUT = Path("docs/index.html")
LATEST = Path("data/latest.json")

_JSON_PLACEHOLDER = "/*__EDITION_JSON__*/"
_BUILD_PLACEHOLDER = "__BUILD_TS__"


def _inject_sports_renderer(html: str) -> str:
    """Inline the modular Sports V2 presentation assets into one static page."""
    css = SPORTS_CSS.read_text(encoding="utf-8")
    performance_css = SPORTS_PERFORMANCE_CSS.read_text(encoding="utf-8")
    js = SPORTS_JS.read_text(encoding="utf-8")
    if "</style>" not in html or "</body>" not in html:
        raise ValueError("edition template is missing Sports renderer injection anchors")
    html = html.replace("</style>", f"\n{css}\n{performance_css}\n  </style>", 1)
    return html.replace("</body>", f"  <script>\n{js}\n  </script>\n</body>", 1)


def render(edition: dict, template_path: Path = TEMPLATE, output_path: Path = OUTPUT) -> Path:
    """Write the rendered edition to output_path; also cache to data/latest.json."""
    template = template_path.read_text(encoding="utf-8")

    edition_json = json.dumps(edition, ensure_ascii=False)
    edition_json = edition_json.replace("</", "<\\/")

    build_ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    html = template.replace(_JSON_PLACEHOLDER, edition_json).replace(_BUILD_PLACEHOLDER, build_ts)
    if edition.get("sports") is not None:
        html = _inject_sports_renderer(html)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    LATEST.parent.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(json.dumps(edition, indent=2, ensure_ascii=False), encoding="utf-8")

    return output_path


if __name__ == "__main__":
    from .images import resolve_images

    edition = json.loads(Path("data/fixtures/edition_sample.json").read_text(encoding="utf-8"))
    resolve_images(edition)
    out = render(edition)
    print(f"OK: wrote {out} ({out.stat().st_size} bytes) and {LATEST}")
