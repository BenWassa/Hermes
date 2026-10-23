"""Opinion-path sources are tagged or routed, never shown as ordinary news (#84).

The three positive cases are the verified Historical Audit baseline HA-05
examples (research/historical-audit/BASELINE_2026-10-22.md). The negative set
pins that straight news under similar-looking paths is left alone.
"""

from __future__ import annotations

import pytest

from src.curate import _trim_input
from src.genre import OPINION_TAG, is_opinion_link, opinion_signal, tag_opinion_in_edition
from src.normalize import CURATION_KEYS, curation_view, normalize
from src.opinion import editorial_without_following

NYT_OPINION = "https://www.nytimes.com/2026/10/22/opinion/palestinians-citizens-israel-election-voting.html"
STAR_COLUMNISTS = (
    "https://www.thestar.com/opinion/star-columnists/"
    "olivia-chow-isn-t-trying-to-lose-toronto-s-mayoral-election-so-what-exactly-is-she-doing/"
    "article_caa967b8-50a8-4646-b0d7-4b71d69cf458.html"
)
STAR_CONTRIBUTORS = (
    "https://www.thestar.com/opinion/contributors/"
    "mayoral-candidates-take-notice-here-is-how-to-make-toronto-a-more-livable-city/"
    "article_5f068411-c37d-41d3-9f74-66b1799a530c.html"
)

BASELINE_CASES = [
    ("nyt", "Palestinian Voters Poised to Influence Pivotal Israeli Election", NYT_OPINION, "world"),
    ("rss", "Olivia Chow is not trying to lose", STAR_COLUMNISTS, "toronto"),
    ("rss", "Mayoral Candidates Urged to Prioritize Livable City Planning", STAR_CONTRIBUTORS, "toronto"),
]

STRAIGHT_NEWS = [
    "https://www.nytimes.com/2026/10/22/world/middleeast/israel-election-polls.html",
    # "opinion" only inside a slug or a longer segment: straight news.
    "https://www.nytimes.com/2026/10/22/us/politics/opinion-poll-shows-lead.html",
    "https://www.nytimes.com/2026/10/22/world/opinion-polls-israel.html",
    "https://www.thestar.com/news/gta/2026/10/22/toronto-council-votes.html",
    "https://www.thestar.com/news/canada/opinion-poll-shows-liberals-ahead/article_1.html",
    "https://www.thestar.com/politics/federal/article_2.html",
    "https://www.thestar.com/opinion-polls/article_3.html",
    "https://www.theguardian.com/world/2026/oct/22/israel-election-opinion-poll",
    "https://www.theguardian.com/commentisfree-fund/2026/oct/22/appeal",
    "https://www.cbc.ca/news/canada/toronto/budget-2026-1.1234567",
    "https://www.cbc.ca/news/politics/opinion-poll-1.7654321",
    # Unknown host: a court *opinion* is not commentary.
    "https://www.courtlistener.com/opinion/123456/smith-v-jones/",
    "https://www.supremecourt.gov/opinions/25pdf/24-1.pdf",
    "",
    None,
]


# --- detection -------------------------------------------------------------

@pytest.mark.parametrize("provider,title,link,hint", BASELINE_CASES)
def test_baseline_cases_are_detected_from_the_url_path(provider, title, link, hint):
    assert opinion_signal(link)
    assert is_opinion_link(link)


@pytest.mark.parametrize("link", STRAIGHT_NEWS)
def test_straight_news_under_similar_paths_is_not_opinion(link):
    assert opinion_signal(link) == ""
    assert not is_opinion_link(link)


@pytest.mark.parametrize(
    "link",
    [
        "https://www.theguardian.com/commentisfree/2026/oct/22/column",
        "https://m.thestar.com/opinion/editorials/article_9.html",
        "https://www.cbc.ca/news/opinion/column-1.1",
        "https://www.nytimes.com/interactive/2026/10/22/opinion/essay.html",
        "https://www.theglobeandmail.com/opinion/article-column/",
        "https://www.washingtonpost.com/opinions/2026/10/22/column/",
    ],
)
def test_other_known_outlet_commentary_paths(link):
    assert is_opinion_link(link)


def test_provider_category_is_corroborating_evidence():
    assert opinion_signal("https://x.example/a", provider="guardian", category="commentisfree")
    assert opinion_signal("https://x.example/a", provider="nyt", category="Opinion")
    assert opinion_signal("https://x.example/a", provider="nyt", category="world") == ""
    assert opinion_signal("https://x.example/a", provider="perigon", category="opinion") == ""


# --- normalize-time metadata and routing ------------------------------------

def _raw(provider, title, link, hint):
    if provider == "nyt":
        return {"_src": "nyt", "_section_hint": hint, "title": title, "abstract": "x",
                "url": link, "section": "world", "published_date": "2026-10-22T05:00:00-04:00"}
    return {"_src": "rss", "_section_hint": hint, "_source_name": "Toronto Star GTA",
            "title": title, "summary": "x", "link": link, "published": "Mon, 19 Oct 2026 10:00:00 GMT"}


@pytest.mark.parametrize("provider,title,link,hint", BASELINE_CASES)
def test_normalize_records_genre_and_routes_to_the_opinion_desk(provider, title, link, hint):
    (story,) = normalize([_raw(provider, title, link, hint)])
    assert story["content_genre"] == "opinion"
    assert story["genre_signal"].startswith("path:")
    assert story["section_hint"] == "opinion"
    assert story["source_section_hint"] == hint


@pytest.mark.parametrize("link", [u for u in STRAIGHT_NEWS if u])
def test_normalize_leaves_straight_news_untouched(link):
    (story,) = normalize([_raw("rss", "A news story", link, "toronto")])
    assert story["content_genre"] == ""
    assert story["genre_signal"] == ""
    assert story["section_hint"] == "toronto"
    assert story["source_section_hint"] == "toronto"


def test_guardian_commentisfree_keeps_its_existing_opinion_hint():
    item = {"_src": "guardian", "_section_hint": "opinion", "webTitle": "Column",
            "webUrl": "https://www.theguardian.com/commentisfree/2026/oct/22/column",
            "sectionId": "commentisfree", "fields": {}, "tags": []}
    (story,) = normalize([item])
    assert story["content_genre"] == "opinion"
    assert story["section_hint"] == "opinion"
    assert story["source_section_hint"] == "opinion"


def test_sports_hint_is_never_rerouted():
    (story,) = normalize([_raw("rss", "Sports column", "https://www.thestar.com/opinion/x.html", "sports")])
    assert story["content_genre"] == "opinion"
    assert story["section_hint"] == "sports"


def test_genre_metadata_never_reaches_the_curation_prompt():
    stories = normalize([_raw(*case) for case in BASELINE_CASES])
    for view in curation_view(stories):
        assert set(view) == set(CURATION_KEYS)
    # Routing changes only the value of an existing key, never the key set.
    assert [v["section_hint"] for v in curation_view(stories)] == ["opinion"] * 3


def test_opinion_routed_items_stay_eligible_for_trim_and_following_dedupe():
    stories = normalize([_raw(*case) for case in BASELINE_CASES])
    assert len(_trim_input(stories)) == 3
    # No Following seeds: the existing function is a pass-through.
    assert editorial_without_following(stories, []) == stories


# --- post-curation render tag ------------------------------------------------

def _edition(*sections):
    return {"sections": [{"id": sid, "label": sid.title(), "stories": stories} for sid, stories in sections]}


def _story(link, tag=None, kicker="ISRAEL"):
    return {"id": "s", "lead": False, "kicker": kicker, "headline": "h", "summary": "s",
            "tag": tag, "link": link}


def test_baseline_cases_render_with_the_opinion_tag_outside_the_opinion_desk():
    edition = _edition(
        ("world", [_story(NYT_OPINION)]),
        ("toronto", [_story(STAR_COLUMNISTS, kicker=None), _story(STAR_CONTRIBUTORS, tag="DEVELOPING")]),
    )
    assert tag_opinion_in_edition(edition) == 3
    stories = [s for sec in edition["sections"] for s in sec["stories"]]
    assert [s["tag"] for s in stories] == [OPINION_TAG] * 3
    # A news-style flag on a column is replaced, not stacked.
    assert stories[2]["tag"] == "OPINION"


def test_straight_news_and_opinion_desk_stories_are_not_modified():
    news = _story("https://www.thestar.com/news/gta/2026/10/22/toronto-council-votes.html", tag="DEVELOPING")
    opinion_desk = _story(NYT_OPINION)
    edition = _edition(("toronto", [news]), ("opinion", [opinion_desk]))
    assert tag_opinion_in_edition(edition) == 0
    assert news["tag"] == "DEVELOPING"
    assert opinion_desk["tag"] is None


def test_an_existing_commentary_tag_is_preserved():
    story = _story(STAR_COLUMNISTS, tag="EDITORIAL")
    assert tag_opinion_in_edition(_edition(("toronto", [story]))) == 0
    assert story["tag"] == "EDITORIAL"


def test_tagging_is_idempotent():
    edition = _edition(("world", [_story(NYT_OPINION)]))
    assert tag_opinion_in_edition(edition) == 1
    assert tag_opinion_in_edition(edition) == 0


def test_browser_renders_the_opinion_chip_for_a_kickerless_story(monkeypatch, tmp_path):
    import json
    from pathlib import Path

    from playwright.sync_api import sync_playwright

    from src import render as render_mod

    edition = json.loads(Path("data/fixtures/edition_sample.json").read_text(encoding="utf-8"))
    front = next(s for s in edition["sections"] if s["id"] == "front")
    front["stories"][0].update(link=NYT_OPINION, kicker=None, tag=None)
    front["stories"][1].update(link="https://www.nytimes.com/2026/10/22/world/news.html", tag=None)
    assert tag_opinion_in_edition(edition) == 1

    monkeypatch.setattr(render_mod, "LATEST", tmp_path / "latest.json")
    artifact = render_mod.render(edition, output_path=tmp_path / "edition.html").resolve()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(artifact.as_uri())
        tagged = page.locator(f'[data-card="{front["stories"][0]["id"]}"] .kicker .tag')
        assert tagged.text_content() == "OPINION"
        assert page.locator(f'[data-card="{front["stories"][1]["id"]}"] .tag').count() == 0
        browser.close()
