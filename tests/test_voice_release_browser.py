from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.voices.model import VoiceArticle
from src.voices.release import ReleaseSummary, render_release_page

UTC = dt.timezone.utc


def fixture_page() -> str:
    article = VoiceArticle(
        key="url:https://publisher.example/long-opinion-piece",
        title="A Deliberately Long Opinion Headline That Must Wrap Cleanly on a Small Phone Without Breaking the Reading Measure",
        canonical_url="https://publisher.example/long-opinion-piece",
        url="https://www.publisher.example/long-opinion-piece",
        publication="Example Review",
        published_at=dt.datetime(2026, 9, 10, 14, 0, tzinfo=UTC),
    )
    summary = ReleaseSummary(
        thesis=(
            "The writer argues that durable institutional reform depends on making responsibility visible "
            "to the public rather than relying on internal assurances alone."
        ),
        takeaways=(
            "Transparent accountability changes incentives before a crisis occurs.",
            "Formal rules matter less when enforcement cannot be observed.",
            "The proposed reform favors simple public feedback over a new administrative layer.",
            "The argument treats public trust as an outcome of institutional design rather than messaging.",
        ),
        why_it_matters="The piece links a narrow governance proposal to the broader problem of declining institutional confidence.",
    )
    return render_release_page(article, writers="Core Writer", summary=summary)


@pytest.mark.parametrize(
    ("width", "height", "label"),
    [
        (412, 915, "pixel-portrait"),
        (360, 740, "compact-portrait"),
        (915, 412, "pixel-landscape"),
    ],
)
def test_release_summary_mobile_render_has_no_overflow_and_primary_link_is_tappable(
    tmp_path, width, height, label
):
    page_path = tmp_path / "index.html"
    page_path.write_text(fixture_page(), encoding="utf-8")
    artifacts = Path("test-artifacts")
    artifacts.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": height},
            has_touch=True,
            is_mobile=width < height,
        )
        page.goto(page_path.resolve().as_uri())
        page.wait_for_load_state("domcontentloaded")

        overflow = page.evaluate(
            "() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth"
        )
        assert overflow <= 1
        assert page.locator("h1").count() == 1
        assert page.get_by_text("Key takeaways", exact=True).count() == 1
        assert page.locator("li").count() == 4
        assert page.get_by_text("Why it matters", exact=True).count() == 1

        read = page.locator("a.read")
        box = read.bounding_box()
        assert box is not None
        assert box["height"] >= 44
        assert read.get_attribute("href") == "https://www.publisher.example/long-opinion-piece"

        page.screenshot(
            path=str(artifacts / f"voices-release-{label}.png"),
            full_page=True,
        )
        browser.close()
