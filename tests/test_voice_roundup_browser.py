from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.voices.registry import Registry, TIER_CORE, Voice
from src.voices.roundup import period_for_id, render_roundup
from src.voices.roundup_state import RoundupItem


def fixture_page() -> tuple[str, list[str]]:
    voices = tuple(
        Voice(id=f"core-{i}", name=f"Core Writer {i}", tier=TIER_CORE)
        for i in range(6)
    )
    registry = Registry(voices=voices)
    period = period_for_id("2026-09-13")
    items = []
    urls = []
    for i in range(6):
        url = f"https://publisher.example/essay-{i}"
        urls.append(url)
        items.append(
            RoundupItem(
                key=f"url:{url}",
                keys=(f"url:{url}",),
                voice_ids=(f"core-{i}",),
                first_seen=period.cutoff - dt.timedelta(hours=i + 1),
                published_at=period.cutoff - dt.timedelta(hours=i + 1),
                title=(
                    "A deliberately realistic weekly opinion headline "
                    f"with enough length to wrap cleanly on a phone {i}"
                ),
                url=url,
                publication=f"Publication {i}",
            )
        )
    return render_roundup(period, items, registry), urls


@pytest.mark.parametrize(
    ("width", "height", "label"),
    [
        (412, 915, "pixel-portrait"),
        (360, 740, "compact-portrait"),
        (915, 412, "pixel-landscape"),
    ],
)
def test_roundup_mobile_render_has_no_overflow_and_keeps_links_tappable(
    tmp_path, width, height, label
):
    html, urls = fixture_page()
    page_path = tmp_path / "index.html"
    page_path.write_text(html, encoding="utf-8")
    artifacts = Path("test-artifacts")
    artifacts.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(page_path.resolve().as_uri())
        page.wait_for_load_state("domcontentloaded")

        overflow = page.evaluate(
            "() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) "
            "- window.innerWidth"
        )
        assert overflow <= 1

        links = page.locator("a.open")
        assert links.count() == 6
        for index in range(links.count()):
            box = links.nth(index).bounding_box()
            assert box is not None
            assert box["height"] >= 44

        assert page.locator("article.piece").count() == 6
        assert page.get_by_text("Open original", exact=False).count() == 6
        hrefs = [links.nth(i).get_attribute("href") for i in range(links.count())]
        assert hrefs == urls

        page.screenshot(
            path=str(artifacts / f"voices-roundup-{label}.png"),
            full_page=True,
        )
        browser.close()
