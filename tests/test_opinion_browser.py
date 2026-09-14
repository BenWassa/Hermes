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
TEMPLATE = Path("template/index.template.html")


def _edition(*, following: bool = True) -> dict:
    edition = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if not following:
        edition.pop("following", None)
        return edition

    edition["following"] = [
        {
            "id": "follow-1",
            "lead": False,
            "kicker": "Jonathan Haidt",
            "headline": "Treasure Your Attention",
            "sub": "Why protecting attention is a civic problem as well as a personal one.",
            "summary": (
                "Jonathan Haidt argues that attention should be treated as a scarce human "
                "resource rather than an unlimited input for digital platforms. The piece "
                "connects individual habits to wider institutional incentives."
            ),
            "analysis": None,
            "time": "After Babel · 7:15 AM",
            "tag": None,
            "sensitivity": False,
            "image": None,
            "link": "https://www.afterbabel.com/p/treasure-your-attention",
            "author": "Jonathan Haidt",
            "publication": "After Babel",
        },
        {
            "id": "follow-2",
            "lead": False,
            "kicker": "Conrad Black, Jane Example",
            "headline": "Institutions and the Long View",
            "sub": None,
            "summary": (
                "Conrad Black sets out an argument about institutional durability and "
                "political memory. The canonical publisher remains the destination for "
                "the complete column."
            ),
            "analysis": None,
            "time": "The New York Sun · Yesterday",
            "tag": None,
            "sensitivity": False,
            "image": None,
            "link": "https://www.nysun.com/article/institutions-and-the-long-view",
            "author": "Conrad Black, Jane Example",
            "publication": "The New York Sun",
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


def test_template_has_no_following_only_card_renderer_or_css():
    template = TEMPLATE.read_text(encoding="utf-8")
    assert ".follow-meta" not in template
    assert ".following-block .card" not in template
    assert "st.following" not in template
    assert "function opinionGroupHtml" in template


@pytest.mark.parametrize("width,height", [(390, 844), (320, 568), (844, 390)])
def test_following_and_today_opinion_share_cards_and_interactions_on_mobile_shapes(
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
        assert page.locator(".follow-meta").count() == 0
        assert page.locator("#following-title").text_content() == "Following"
        assert page.locator("#today-opinion-title").text_content() == "Today’s Opinion"

        first = page.locator('[data-card="follow-1"]')
        second = page.locator('[data-card="follow-2"]')
        assert first.locator(".kicker").text_content() == "Jonathan Haidt"
        assert first.locator(".time").text_content() == "After Babel · 7:15 AM"
        assert second.locator(".kicker").text_content() == "Conrad Black, Jane Example"
        assert second.locator(".time").text_content() == "The New York Sun · Yesterday"
        assert "lead" not in (first.get_attribute("class") or "").split()
        assert "lead" not in (second.get_attribute("class") or "").split()

        # Both desks terminate at the exact same card structure and renderer.
        assert first.locator(":scope > .row > .row-main > .headline").count() == 1
        ordinary = page.locator(".today-opinion .card").first
        assert ordinary.locator(":scope > .row > .row-main > .headline").count() == 1
        assert page.locator(".today-opinion .card.lead").count() >= 1

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

        page.screenshot(path=str(ARTIFACTS / f"opinion-{width}x{height}.png"))

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

        # Ask AI still receives the retained non-rendering provenance fields.
        claude_href = first.locator('a[href^="https://claude.ai/new?q="]').get_attribute("href")
        assert claude_href is not None
        assert "Jonathan%20Haidt" in claude_href
        assert "After%20Babel" in claude_href

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
