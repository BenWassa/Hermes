"""Article identity: merging duplicates without collapsing distinct pieces."""

from __future__ import annotations

import datetime as dt

from src.voices.dedupe import group_syndication, identity_keys, merge_observations
from src.voices.model import Attribution, Author, Observation
from tests.conftest import NOW


def obs(url, *, title="Attention and the Commons", adapter="rss", provider="rss",
        source_key="rss:feed", article_id="", published=None, byline="Jonathan Haidt",
        authors=None, reprint=False, reprint_group="", publication="After Babel",
        canonical=None, description="") -> Observation:
    from src.voices.urls import canonical_url

    return Observation(
        adapter=adapter,
        source_key=source_key,
        provider=provider,
        title=title,
        url=url,
        canonical_url=canonical if canonical is not None else canonical_url(url),
        description=description,
        publication=publication,
        published_at=published if published is not None else NOW - dt.timedelta(hours=3),
        byline=byline,
        authors=tuple(authors or (Author(name="Jonathan Haidt"),)),
        provider_article_id=article_id,
        reprint=reprint,
        reprint_group_id=reprint_group,
    )


def test_the_same_article_from_two_adapters_becomes_one():
    from_feed = obs("https://www.afterbabel.com/p/attention?utm_source=substack")
    from_pool = obs(
        "https://afterbabel.com/p/attention",
        adapter="pool", provider="perigon", source_key="pool:perigon",
        article_id="perigon-123", publication="After Babel",
    )
    merged = merge_observations([from_feed, from_pool])
    assert len(merged) == 1
    assert len(merged[0].observations) == 2
    assert merged[0].canonical_url == "https://afterbabel.com/p/attention"
    assert merged[0].discovered_via == ["rss:feed", "pool:perigon"]


def test_merging_is_independent_of_observation_order():
    a = obs("https://www.afterbabel.com/p/attention?utm_source=substack")
    b = obs("https://afterbabel.com/p/attention", adapter="pool", source_key="pool:perigon")
    forward = merge_observations([a, b])
    backward = merge_observations([b, a])
    assert [x.key for x in forward] == [x.key for x in backward]


def test_tracking_parameters_alone_do_not_create_a_second_article():
    variants = [
        obs("https://afterbabel.com/p/attention"),
        obs("https://afterbabel.com/p/attention?utm_campaign=weekly"),
        obs("https://www.afterbabel.com/p/attention?fbclid=abc#top"),
    ]
    assert len(merge_observations(variants)) == 1


def test_two_different_articles_stay_two_articles():
    merged = merge_observations([
        obs("https://afterbabel.com/p/attention", title="Attention and the Commons"),
        obs("https://afterbabel.com/p/phones", title="Phones and Childhood"),
    ])
    assert len(merged) == 2


def test_same_title_on_different_hosts_does_not_merge():
    merged = merge_observations([
        obs("https://theatlantic.com/ideas/attention", publication="The Atlantic"),
        obs("https://nationalpost.com/opinion/attention", publication="National Post"),
    ])
    assert len(merged) == 2


def test_a_provider_id_rejoins_two_sightings_from_one_provider():
    """Same provider, same id, URL moved: still one article."""
    merged = merge_observations([
        obs("https://theguardian.com/commentisfree/2026/sep/05/rivers",
            adapter="guardian_contributor", provider="guardian",
            article_id="commentisfree/2026/sep/05/rivers"),
        obs("https://theguardian.com/environment/2026/sep/05/rivers",
            adapter="pool", provider="guardian",
            article_id="commentisfree/2026/sep/05/rivers"),
    ])
    assert len(merged) == 1


def test_provider_ids_from_different_providers_never_collide():
    left = obs("https://a.example.com/x", provider="guardian", article_id="shared-id")
    right = obs("https://b.example.com/y", provider="perigon", article_id="shared-id")
    assert not (identity_keys(left) & identity_keys(right))
    assert len(merge_observations([left, right])) == 2


def test_the_same_host_fingerprint_rejoins_a_moved_url():
    merged = merge_observations([
        obs("https://nysun.com/article/the-long-retreat"),
        obs("https://nysun.com/article/the-long-retreat-of-the-administrative-state"),
    ])
    assert len(merged) == 1


def test_the_fingerprint_needs_a_matching_day():
    merged = merge_observations([
        obs("https://nysun.com/article/one", published=NOW - dt.timedelta(hours=3)),
        obs("https://nysun.com/article/two", published=NOW - dt.timedelta(days=4)),
    ])
    assert len(merged) == 2


def test_attributions_merge_across_observations():
    a = obs("https://afterbabel.com/p/attention")
    b = obs("https://afterbabel.com/p/attention?utm_source=x", adapter="pool", source_key="pool:perigon")
    merged = merge_observations([a, b], {
        0: [Attribution("jonathan-haidt", "byline_alias", "byline 'Jonathan Haidt'")],
        1: [Attribution("jonathan-haidt", "provider_author_id", "perigon:perigon-jhaidt-001")],
    })
    assert len(merged) == 1
    assert merged[0].voice_ids == ["jonathan-haidt"]
    # The strongest evidence is what gets reported for the Voice.
    assert merged[0].evidence_for("jonathan-haidt").evidence == "provider_author_id"
    assert len(merged[0].attributions) == 2  # both are kept for diagnosis


def test_an_observation_with_no_keyable_identity_survives_alone():
    weird = obs("mailto:someone@example.com", title="No URL At All")
    merged = merge_observations([weird, obs("https://afterbabel.com/p/attention")])
    assert len(merged) == 2


# --- syndication ----------------------------------------------------------

def test_a_reprint_group_is_grouped_not_merged():
    original = obs("https://theatlantic.com/ideas/attention", publication="The Atlantic",
                   provider="perigon", article_id="p1", published=NOW - dt.timedelta(hours=8))
    reprint = obs("https://nationalpost.com/opinion/attention", publication="National Post",
                  provider="perigon", article_id="p2", published=NOW - dt.timedelta(hours=4),
                  reprint=True, reprint_group="reprint-group-attention")
    articles = group_syndication(merge_observations([original, reprint]))

    assert len(articles) == 2, "syndicated copies stay distinct articles"
    primaries = [a for a in articles if a.syndication_primary]
    assert len(primaries) == 1
    assert "theatlantic.com" in primaries[0].canonical_url
    copy = next(a for a in articles if not a.syndication_primary)
    assert copy.syndicated_from == primaries[0].key
    assert copy.syndication_group == articles[0].syndication_group


def test_syndication_without_a_provider_flag_uses_title_author_and_day():
    articles = group_syndication(merge_observations(
        [obs("https://theatlantic.com/ideas/attention", publication="The Atlantic",
             published=NOW - dt.timedelta(hours=9)),
         obs("https://nationalpost.com/opinion/attention", publication="National Post",
             published=NOW - dt.timedelta(hours=5))],
        {0: [Attribution("jonathan-haidt", "byline_alias", "x")],
         1: [Attribution("jonathan-haidt", "byline_alias", "y")]},
    ))
    assert sum(1 for a in articles if a.syndication_primary) == 1


def test_a_different_author_prevents_syndication_grouping():
    articles = group_syndication(merge_observations([
        obs("https://a-paper.com/x", publication="A", byline="Jonathan Haidt",
            authors=(Author(name="Jonathan Haidt"),)),
        obs("https://b-paper.com/x", publication="B", byline="Priya Raman",
            authors=(Author(name="Priya Raman"),)),
    ]))
    assert all(a.syndication_primary for a in articles)


def test_a_different_day_prevents_syndication_grouping():
    articles = group_syndication(merge_observations([
        obs("https://a-paper.com/x", publication="A", published=NOW - dt.timedelta(hours=2)),
        obs("https://b-paper.com/x", publication="B", published=NOW - dt.timedelta(days=9)),
    ]))
    assert all(a.syndication_primary for a in articles)


def test_a_single_publisher_is_never_a_syndication_group():
    articles = group_syndication(merge_observations([
        obs("https://afterbabel.com/p/attention"),
        obs("https://afterbabel.com/p/phones", title="Phones and Childhood"),
    ]))
    assert all(a.syndication_primary for a in articles)
