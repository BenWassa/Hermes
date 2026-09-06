"""Browser acceptance for the exact production Opinion renderer.

These tests intentionally render `template/index.template.html` through
`src.render.render`, then open that generated static artifact in Chromium. They
exercise the real card/tabs/Ask-AI JavaScript instead of asserting markup only.
Viewport screenshots and the rendered HTML are retained under `test-artifacts/`
for CI inspection.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src import render as render_mod

ARTIFACTS = Path("test-artifacts")
FIXTURE = Path("data/fixtures/edition_sample.json")


def _edition(*, following: bool = True) -> dict:
    edition = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if not following:
        edition.pop("following", None)
        return edition

    edition["following"] = [
        {
            "id": "follow-1",
            "lead": False,
            "kicker": None,
            "headline": "Treasure Your Attention",
            "sub": "Why protecting attention is a civic problem as well as a personal one.",
            "summary": (
                "Jonathan Haidt argues that attention should be treated as a scarce human "
                "resource rather than an unlimited input for digital platforms. The piece "
                "connects individual habits to wider institutional incentives."
            ),
            "analysis": None,
            "time": "7:15 AM",
            "tag": None,
            "sensitivity": False,
            "image": None,
            "link": "https://www.afterbabel.com/p/treasure-your-attention",
            "author": "Jonathan Haidt",
            "publication": "After Babel",
            "paywalled": False,
            "voice_ids": ["jonathan-haidt"],
            "canonical_key": "url:https://afterbabel.com/p/treasure-your-attention",
            "following": True,
        },
        {
            "id": "follow-2",
            "lead": False,
            "kicker": None,
            "headline": "Institutions and the Long View",
            "sub": None,
            "summary": (
                "Conrad Black sets out an argument about institutional durability and "
                "political memory. The canonical publisher remains the destination for "
                "the complete column."
            ),
            "analysis": None,
            "time": "Yesterday",
            "tag": None,
            "sensitivity": False,
            "image": None,
            "link": "https://www.nysun.com/article/institutions-and-the-long-view",
            "author": "Conrad Black, Jane Example",
            "publication": "The New York Sun",
            "paywalled": True,
            "voice_ids": ["conrad-black"],
            "canonical_key": "url:https://nysun.com/article/institutions-and-the-long-view",
            "following": True,
        },
    ]
    return edition


def _render(monkeypatch: pytest.MonkeyPatch, edition: dict) -> Path:
    ARTIFACTS.mkdir(exist_ok=True)
    monkeypatch.setattr(render_mod, "LATEST", ARTIFACTS / "latest-browser-edition.json")
    return render_mod.render(edition, output_path=ARTIFACTS / "following-edition.html").resolve()


def _open_opinion(page) -> None:
    page.locator('[data-tab="opinion"]').click()
    page.locator("#following-title").wait_for(state="visible")


@pytest.mark.parametrize("width,height", [(390, 844), (320, 568), (844, 390)])
def test_following_is_compact_distinct_and_interactive_on_mobile_shapes(
    monkeypatch: pytest.MonkeyPatch, width: int, height: int
):
    artifact = _render(monkeypatch, _edition())

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": width, "height": height},
            has_touch=True,
            is_mobile=True,
        )
        page = context.new_page()
        page.goto(artifact.as_uri())
        _open_opinion(page)

        assert page.locator(".following-block .card").count() == 2
        # `text-transform: uppercase` is intentional visual styling. Use
        # text_content() to assert the semantic/authored labels rather than the
        # browser's transformed presentation returned by inner_text().
        assert page.locator("#following-title").text_content() == "Following"
        assert page.locator("#today-opinion-title").text_content() == "Today’s Opinion"
        assert "Jonathan Haidt · After Babel · 7:15 AM" in page.locator(
            '[data-card="follow-1"] .follow-meta'
        ).inner_text()
        assert "Conrad Black, Jane Example · The New York Sun" in page.locator(
            '[data-card="follow-2"] .follow-meta'
        ).inner_text()

        # The strip may scroll internally, but the paper itself must not widen
        # beyond the phone/landscape viewport.
        overflow = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        assert overflow <= 1

        # Full-page screenshots composite sticky elements at their current
        # scroll position and can falsely look overlapped. Assert actual viewport
        # geometry instead: Following must start below the sticky tab strip, and
        # Today's Opinion must start after the complete Following block.
        tabs_box = page.locator(".tabs").bounding_box()
        following_title_box = page.locator("#following-title").bounding_box()
        following_block_box = page.locator(".following-block").bounding_box()
        today_box = page.locator(".today-opinion").bounding_box()
        assert tabs_box is not None
        assert following_title_box is not None
        assert following_block_box is not None
        assert today_box is not None
        assert following_title_box["y"] >= tabs_box["y"] + tabs_box["height"] - 1
        assert today_box["y"] >= following_block_box["y"] + following_block_box["height"] - 1

        # Save what a reader actually sees at the requested viewport, not a
        # browser-composited full-document representation of sticky controls.
        page.screenshot(path=str(ARTIFACTS / f"opinion-{width}x{height}.png"))

        first = page.locator('[data-card="follow-1"]')
        first.tap()
        assert first.get_attribute("aria-expanded") == "true"
        assert first.locator(".sumtext").is_visible()
        assert first.locator(".readmore").get_attribute("href") == (
            "https://www.afterbabel.com/p/treasure-your-attention"
        )

        first.locator(".askai").tap()
        assert first.locator(".ask-panel").get_attribute("class") == "ask-panel open"
        assert first.locator('a[href^="https://claude.ai/new?q="]').count() == 1
        assert first.locator('a[href^="https://chatgpt.com/?q="]').count() == 1

        # Keyboard activation remains real card behavior after the Following
        # surface is introduced.
        second = page.locator('[data-card="follow-2"]')
        second.focus()
        page.keyboard.press("Enter")
        assert second.get_attribute("aria-expanded") == "true"
        assert second.locator(".readmore").get_attribute("href") == (
            "https://www.nysun.com/article/institutions-and-the-long-view"
        )

        browser.close()


def test_zero_followed_stories_is_the_normal_existing_opinion_state(monkeypatch: pytest.MonkeyPatch):
    artifact = _render(monkeypatch, _edition(following=False))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(artifact.as_uri())
        page.locator('[data-tab="opinion"]').click()

        assert page.locator(".following-block").count() == 0
        assert page.locator("#following-title").count() == 0
        assert page.locator('.stories .card').count() > 0
        browser.close()


def test_reduced_motion_and_touch_targets_remain_intact(monkeypatch: pytest.MonkeyPatch):
    artifact = _render(monkeypatch, _edition())

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            has_touch=True,
            is_mobile=True,
            reduced_motion="reduce",
        )
        page = context.new_page()
        page.goto(artifact.as_uri())
        _open_opinion(page)

        card_transition_ms = page.locator('[data-card="follow-1"]').evaluate(
            """el => {
              const raw = getComputedStyle(el).transitionDuration.split(',')[0].trim();
              return raw.endsWith('ms') ? parseFloat(raw) : parseFloat(raw) * 1000;
            }"""
        )
        assert card_transition_ms <= 1

        page.locator('[data-card="follow-1"]').tap()
        for selector in (".readmore", ".askai"):
            box = page.locator('[data-card="follow-1"] ' + selector).bounding_box()
            assert box is not None
            assert box["height"] >= 44

        browser.close()
