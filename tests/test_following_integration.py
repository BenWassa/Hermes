"""Issue #11: deterministic Following inside the finite Opinion desk."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from types import SimpleNamespace

from src import build as build_mod
from src.opinion import (
    build_following_cards,
    editorial_without_following,
    following_seed,
    following_seeds,
    suppress_opinion_duplicates,
)
from src.voices.model import Attribution, Author, Observation, VoiceArticle
from src.voices.registry import Registry, Voice
from src.voices.urls import url_key

NOW = dt.datetime(2026, 9, 5, 11, 30, tzinfo=dt.timezone.utc)
TODAY = dt.date(2026, 9, 5)
REGISTRY = Registry(
    voices=(
        Voice(id="haidt", name="Jonathan Haidt"),
        Voice(id="black", name="Conrad Black"),
        Voice(id="peterson", name="Jordan Peterson"),
    )
)


def article(
    key: str,
    voice_id: str = "haidt",
    *,
    url: str | None = None,
    title: str = "A new argument",
    publication: str = "After Babel",
    description: str = "A concise source description of the argument.",
    image: str | None = "https://images.example/item.jpg",
    paywalled: bool | None = False,
    byline: str = "By Jonathan Haidt",
    authors: tuple[Author, ...] = (Author(name="Jonathan Haidt"),),
    hours_ago: int = 2,
    extra_voices: tuple[str, ...] = (),
) -> VoiceArticle:
    link = url or f"https://example.com/opinion/{key}?utm_source=test"
    canonical = link.split("?", 1)[0]
    observation = Observation(
        adapter="pool",
        source_key="pool:test",
        title=title,
        url=link,
        canonical_url=canonical,
        description=description,
        image=image,
        publication=publication,
        published_at=NOW - dt.timedelta(hours=hours_ago),
        paywalled=paywalled,
        byline=byline,
        authors=authors,
    )
    attrs = [Attribution(voice_id, "byline_alias", byline)]
    attrs.extend(Attribution(v, "byline_alias", byline) for v in extra_voices)
    return VoiceArticle(
        key=url_key(canonical),
        title=title,
        canonical_url=canonical,
        url=link,
        publication=publication,
        description=description,
        image=image,
        published_at=observation.published_at,
        paywalled=paywalled,
        identity_keys=frozenset({url_key(canonical)}),
        observations=[observation],
        attributions=attrs,
    )


def test_no_followed_work_leaves_the_editorial_pool_unchanged():
    stories = [{"section_hint": "opinion", "link": "https://example.com/a"}]
    assert editorial_without_following(stories, []) == stories


def test_following_seed_preserves_coauthors_publication_and_canonical_paywall_destination():
    item = article(
        "coauthored",
        url="https://www.example.com/essay?utm_campaign=x",
        publication="Example Review",
        paywalled=True,
        byline="By Jonathan Haidt and Jean Twenge",
        authors=(Author(name="Jonathan Haidt"), Author(name="Jean Twenge")),
    )
    seed = following_seed(item, REGISTRY)

    assert seed["author"] == "Jonathan Haidt, Jean Twenge"
    assert seed["publication"] == "Example Review"
    assert seed["paywalled"] is True
    assert seed["link"] == "https://example.com/essay"


def test_duplicate_is_removed_from_ordinary_opinion_but_not_another_news_desk():
    followed = following_seeds([article("same")], REGISTRY)
    stories = [
        {
            "title": "Opinion copy",
            "section_hint": "opinion",
            "canonical_url": "https://example.com/opinion/same",
            "link": "https://example.com/opinion/same?utm_source=desk",
        },
        {
            "title": "News treatment",
            "section_hint": "world",
            "canonical_url": "https://example.com/opinion/same",
            "link": "https://example.com/opinion/same",
        },
        {
            "title": "Different opinion",
            "section_hint": "opinion",
            "canonical_url": "https://example.com/opinion/other",
            "link": "https://example.com/opinion/other",
        },
    ]

    remaining = editorial_without_following(stories, followed)
    assert [story["title"] for story in remaining] == ["News treatment", "Different opinion"]


def test_model_cannot_drop_relink_or_rename_a_selected_followed_item():
    seeds = following_seeds([article("fixed")], REGISTRY)
    cards = build_following_cards(
        seeds,
        [
            {
                "key": seeds[0]["key"],
                "headline": "Model tried to replace it",
                "link": "https://wrong.example/",
                "summary": "The model may write this summary, and nothing more authoritative.",
                "sensitivity": False,
            }
        ],
        today=TODAY,
    )

    assert len(cards) == 1
    assert cards[0]["headline"] == "A new argument"
    assert cards[0]["link"] == "https://example.com/opinion/fixed"
    assert cards[0]["summary"].startswith("The model may write")
    assert cards[0]["following"] is True


def test_missing_model_result_description_and_image_still_yield_a_coherent_card():
    seed = following_seed(
        article("minimal", description="", image=None, publication="The New York Sun", paywalled=True),
        REGISTRY,
    )
    cards = build_following_cards([seed], [], today=TODAY)

    assert len(cards) == 1
    assert cards[0]["image"] is None
    assert cards[0]["summary"] == (
        "New writing from Jonathan Haidt at The New York Sun. "
        "Open the original piece for the full argument."
    )
    assert cards[0]["paywalled"] is True
    assert cards[0]["link"] == "https://example.com/opinion/minimal"


def test_several_selected_voices_and_items_keep_fixed_finite_order_even_if_model_reorders():
    items = [
        article("a", "haidt", hours_ago=1),
        article("b", "black", byline="By Conrad Black", authors=(Author(name="Conrad Black"),), hours_ago=2),
        article("c", "peterson", byline="By Jordan Peterson", authors=(Author(name="Jordan Peterson"),), hours_ago=3),
        article("d", "haidt", hours_ago=4),
    ]
    seeds = following_seeds(items, REGISTRY)
    model = [
        {"key": seed["key"], "summary": f"Summary {index}", "sensitivity": False}
        for index, seed in reversed(list(enumerate(seeds)))
    ]

    cards = build_following_cards(seeds, model, today=TODAY)
    assert [card["canonical_key"] for card in cards] == [seed["key"] for seed in seeds]
    assert len(cards) == 4
    assert {card["author"] for card in cards} == {
        "Jonathan Haidt", "Conrad Black", "Jordan Peterson"
    }


def test_postpass_makes_following_win_if_editor_returns_duplicate_anyway():
    seeds = following_seeds([article("same")], REGISTRY)
    edition = {
        "sections": [
            {
                "id": "opinion",
                "label": "Opinion",
                "stories": [
                    {
                        "id": "o1",
                        "lead": True,
                        "headline": "Duplicate",
                        "link": "https://www.example.com/opinion/same?utm_medium=x",
                    },
                    {
                        "id": "o2",
                        "lead": False,
                        "headline": "Independent discovery",
                        "link": "https://example.com/opinion/other",
                    },
                ],
            }
        ]
    }

    assert suppress_opinion_duplicates(edition, seeds) == 1
    assert [story["id"] for story in edition["sections"][0]["stories"]] == ["o2"]
    assert edition["sections"][0]["stories"][0]["lead"] is True


def test_voice_source_failure_remains_local_to_the_morning_build(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(build_mod.weather_mod, "get_weather", lambda: {})
    monkeypatch.setattr(build_mod, "fetch_all", lambda: [object()])
    monkeypatch.setattr(
        build_mod,
        "normalize",
        lambda raw: [
            {
                "title": "Ordinary story",
                "description": "Description",
                "source": "Example",
                "section_hint": "world",
                "pub_date": "2026-09-05T10:00:00Z",
                "image": None,
                "link": "https://example.com/world",
            }
        ],
    )
    monkeypatch.setattr(build_mod, "load_registry", lambda path: REGISTRY)
    monkeypatch.setattr(
        build_mod,
        "discover",
        lambda registry, pool: SimpleNamespace(
            fresh=[], failures=[{"source": "rss", "error": "network down"}]
        ),
    )

    captured: dict = {}

    def fake_curate(stories, weather=None, following=None):
        captured["stories"] = stories
        captured["following"] = following
        return {
            "date": "Saturday, September 5, 2026",
            "weather": {},
            "sections": [
                {
                    "id": "world",
                    "label": "World",
                    "stories": [
                        {
                            "id": "w1",
                            "headline": "Ordinary story",
                            "summary": "Still publishes.",
                            "image": None,
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr(build_mod, "curate", fake_curate)
    monkeypatch.setattr(build_mod, "resolve_images", lambda edition: None)
    out = tmp_path / "index.html"
    out.write_text("ok")
    monkeypatch.setattr(build_mod, "render", lambda edition: out)

    assert build_mod.main() == 0
    assert captured["following"] == []
    assert len(captured["stories"]) == 1
