"""The representative acceptance audit for issue #10.

One end-to-end run over recorded fixtures, proving that every case the issue
names is handled by the same generic machinery. The audit voices exist only as
data in ``tests/fixtures/voices/acceptance.json``; the guard at the bottom of
this file asserts that no acceptance name appears anywhere in ``src/``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.voices.discover import default_budget, discover
from src.voices.following import select_following, suppress_duplicates
from tests.conftest import FakeHttp, FakeResponse, fixture_bytes, fixture_json, fixture_text

SRC = Path(__file__).resolve().parents[1] / "src"


@pytest.fixture(autouse=True)
def provider_keys(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("PERIGON_API_KEY", "test-key")


@pytest.fixture
def pool():
    """The ordinary morning pool, normalized as the live build produces it."""
    from src.normalize import normalize

    guardian = fixture_json("guardian", "contributor_search.json")["response"]["results"]
    for item in guardian:
        item["_src"] = "guardian"
        item["_section_hint"] = "opinion"
    nyt = fixture_json("nyt", "opinion_top_stories.json")["results"]
    for item in nyt:
        item["_src"] = "nyt"
        item["_section_hint"] = "opinion"
    return normalize(guardian + nyt)


@pytest.fixture
def audit(acceptance_registry, window, pool):
    http = FakeHttp(
        {
            "afterbabel.com": FakeResponse(
                content=fixture_bytes("rss", "multi_author_publication.xml")),
            "drjordanbpeterson.substack.com": FakeResponse(
                content=fixture_bytes("rss", "personal_newsletter.xml")),
            "guardianapis.com": FakeResponse(
                payload=fixture_json("guardian", "contributor_search.json")),
            "perigon.io": FakeResponse(
                payload=fixture_json("perigon", "journalist_articles.json")),
            "nysun.com": FakeResponse(
                text=fixture_text("author_pages", "jsonld_author_archive.html")),
            "example-herald.com": FakeResponse(
                text=fixture_text("author_pages", "structural_author_archive.html")),
        },
        budget=default_budget(),
    )
    return discover(acceptance_registry, pool=pool, window=window, http=http)


def articles_for(result, voice_id):
    return [a for a in result.articles if voice_id in a.voice_ids]


def evidence_for(result, voice_id):
    return {a.evidence_for(voice_id).evidence for a in articles_for(result, voice_id)}


# --- the named acceptance voices ------------------------------------------

def test_jonathan_haidt_is_discovered_across_two_publishing_surfaces(audit):
    """A multi-author newsletter plus a cross-publication journalist identity."""
    articles = articles_for(audit, "jonathan-haidt")
    hosts = {a.canonical_url.split("/")[2] for a in articles}
    assert {"afterbabel.com", "theatlantic.com"} <= hosts
    assert evidence_for(audit, "jonathan-haidt") == {"byline_alias", "provider_author_id"}


def test_jordan_peterson_is_discovered_from_a_personal_newsletter(audit):
    articles = articles_for(audit, "jordan-peterson")
    assert {a.title for a in articles} == {"On Responsibility and Order", "Notes From the Tour"}
    # The feed carries no author metadata at all; the source itself is the proof.
    assert evidence_for(audit, "jordan-peterson") == {"source_scope"}
    assert all(a.byline == "" for a in articles)


def test_conrad_black_is_discovered_from_a_publication_author_archive(audit):
    articles = articles_for(audit, "conrad-black")
    assert "The Long Retreat of the Administrative State" in {a.title for a in articles}
    assert evidence_for(audit, "conrad-black") == {"source_scope"}
    assert all("nysun.com" in a.canonical_url for a in articles)


def test_a_guardian_contributor_resolves_on_canonical_contributor_metadata(audit):
    articles = articles_for(audit, "george-monbiot")
    assert "Rivers and the public realm" in {a.title for a in articles}
    assert evidence_for(audit, "george-monbiot") == {"provider_author_id"}


def test_an_nyt_opinion_writer_resolves_from_the_stream_hermes_already_fetches(audit):
    articles = articles_for(audit, "david-brooks")
    assert "The Quiet Part of the Bargain" in {a.title for a in articles}
    assert evidence_for(audit, "david-brooks") == {"byline_alias"}
    # No NYT request was made for him: the Opinion stream was already fetched.
    assert "nyt" not in audit.budget


def test_a_multi_author_article_attributes_only_the_followed_writers(audit):
    # One followed author, one stranger: the stranger contributes nothing.
    nyt_joint = next(a for a in audit.articles if a.title == "Two Views on the Budget")
    assert nyt_joint.voice_ids == ["david-brooks"]
    assert [author.name for author in nyt_joint.authors] == ["David Brooks", "Marisol Vega"]

    # Two followed authors on one piece: both are credited, once each.
    joint = next(a for a in audit.articles if a.title == "Two authors on water")
    assert sorted(joint.voice_ids) == ["amelia-hargreaves", "george-monbiot"]
    assert [author.name for author in joint.authors] == ["George Monbiot", "Amelia Hargreaves"]
    assert len(joint.attributions) == 2


def test_an_ambiguous_common_name_is_never_attributed_on_a_byline(audit, acceptance_registry, window):
    """A different John Smith writing elsewhere must not become the followed one."""
    import feedparser

    from src.normalize import normalize

    parsed = feedparser.parse(fixture_bytes("rss", "atom_common_name.xml"))
    entries = list(parsed.entries)
    for entry in entries:
        entry["_src"] = "rss"
        entry["_section_hint"] = "toronto"
        entry["_source_name"] = "Municipal Notes"
    other_smith = normalize(entries)
    assert other_smith[0]["authors"] == [{"name": "John Smith"}], "the byline was read"
    result = discover(acceptance_registry, pool=other_smith, window=window, fetch=False)
    assert articles_for(result, "john-smith") == []
    assert [r.reason for r in result.rejections] == ["requires_provider_id"]


def test_a_story_merely_about_a_followed_writer_is_not_their_article(audit):
    titles = {a.title for a in audit.articles}
    assert "What Jonathan Haidt Missed About Phones" not in titles
    assert "What George Monbiot gets wrong about rivers" not in titles
    assert "Schools debate the Haidt thesis" not in titles


# --- identity behaviour across the whole run ------------------------------

def test_the_same_article_found_by_two_adapters_appears_once(audit):
    """The Guardian column arrives via the contributor query and the pool."""
    rivers = [a for a in audit.articles if "rivers-and-the-public-realm" in a.canonical_url]
    assert len(rivers) == 1
    assert set(rivers[0].discovered_via) == {
        "guardian_contributor:profile/georgemonbiot", "pool:guardian"}


def test_a_reprint_is_grouped_rather_than_shown_twice(audit):
    group = [a for a in audit.articles if a.title == "Attention and the Commons"]
    assert len(group) == 2, "both copies survive with their own canonical URLs"
    primaries = [a for a in group if a.syndication_primary]
    assert len(primaries) == 1
    assert "theatlantic.com" in primaries[0].canonical_url
    assert group[0].syndication_group == group[1].syndication_group


def test_the_following_block_is_finite_and_shows_each_piece_once(audit):
    from src import config

    chosen = select_following(
        audit.fresh, cap=config.VOICE_FOLLOWING_CAP, per_voice=config.VOICE_MAX_PER_VOICE
    )
    assert 0 < len(chosen) <= config.VOICE_FOLLOWING_CAP
    assert len({a.key for a in chosen}) == len(chosen)
    assert all(a.syndication_primary for a in chosen)
    counts: dict[str, int] = {}
    for item in chosen:
        counts[item.voice_ids[0]] = counts.get(item.voice_ids[0], 0) + 1
    assert max(counts.values()) <= config.VOICE_MAX_PER_VOICE


def test_a_followed_piece_also_chosen_by_the_editor_is_shown_once(audit):
    from src import config

    chosen = select_following(
        audit.fresh, cap=config.VOICE_FOLLOWING_CAP, per_voice=config.VOICE_MAX_PER_VOICE
    )
    # The editor independently picked the newest followed piece, with its own
    # tracking parameters on the link.
    duplicated = chosen[0]
    edition_links = [f"{duplicated.canonical_url}?CMP=share_btn_url&utm_source=daily"]

    remaining = suppress_duplicates(chosen, edition_links)
    assert len(remaining) == len(chosen) - 1
    assert duplicated.key not in {a.key for a in remaining}


def test_paywalled_material_is_linked_not_reproduced(audit):
    for article in articles_for(audit, "conrad-black"):
        assert article.canonical_url.startswith("https://nysun.com/article/")
        assert article.paywalled is True
        # Discovery keeps the headline, the date and the canonical link. No
        # body text is fetched, stored, or rendered.
        assert article.description == ""

    atlantic = next(a for a in audit.articles if "theatlantic.com" in a.canonical_url)
    assert atlantic.paywalled is True, "the provider's own paywall flag survives"


def test_the_downstream_record_shape_is_stable(audit):
    """The contract #11 and #12 build on."""
    record = audit.fresh[0].as_dict()
    assert set(record) == {
        "key", "title", "canonical_url", "link", "source", "description", "image",
        "pub_date", "paywalled", "byline", "authors", "voice_ids", "discovered_via",
        "syndication", "attributions", "observations",
    }
    assert record["voice_ids"] and record["link"].startswith("http")
    assert set(record["syndication"]) == {"group", "primary", "syndicated_from"}
    assert all(set(a) >= {"voice_id", "evidence", "detail"} for a in record["attributions"])


def test_every_attribution_in_the_run_can_be_explained(audit):
    for article in audit.articles:
        assert article.voice_ids
        for voice_id in article.voice_ids:
            evidence = article.evidence_for(voice_id)
            assert evidence and evidence.detail and evidence.evidence


def test_the_whole_run_costs_a_handful_of_requests(audit):
    assert audit.budget == {"author_page": 2, "guardian": 1, "perigon": 1, "rss": 2}
    assert sum(audit.budget.values()) == 6


# --- the structural invariant ---------------------------------------------

ACCEPTANCE_NAMES = [
    "haidt", "peterson", "conrad", "monbiot", "brooks", "hargreaves",
    "afterbabel", "nysun", "jordanbpeterson", "theatlantic",
]


def _code_corpus(path: Path) -> str:
    """Every identifier and non-docstring literal in a module.

    Prose is excluded on purpose: documenting an acceptance case is fine, and
    what must not exist is a *code path* keyed to a person - a
    ``fetch_jonathan_haidt()``, or an ``if tag == "profile/georgemonbiot"``.
    """
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))

    parts: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            parts.append(node.value)
        elif isinstance(node, ast.Name):
            parts.append(node.id)
        elif isinstance(node, ast.Attribute):
            parts.append(node.attr)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            parts.append(node.name)
        elif isinstance(node, ast.arg):
            parts.append(node.arg)
    return " ".join(parts).lower()


def test_no_acceptance_voice_appears_in_source_control_flow():
    """Voices are data. No person may reach fetch, resolution, or config."""
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        corpus = _code_corpus(path)
        for name in ACCEPTANCE_NAMES:
            # Plain substring, not a word boundary: a person-specific path
            # hides just as well inside "fetch_jonathan_haidt" or
            # "profile/georgemonbiot" as it does as a standalone word.
            if name in corpus:
                offenders.append(f"{path.relative_to(SRC.parent)}: {name}")
    assert offenders == [], offenders


def test_the_guard_would_catch_a_person_specific_code_path(tmp_path):
    """The guard above is only worth having if it actually fails."""
    offending = tmp_path / "bad.py"
    offending.write_text(
        'def fetch_jonathan_haidt():\n'
        '    """A per-person fetch function, which must never exist."""\n'
        '    return []\n',
        encoding="utf-8",
    )
    assert "haidt" in _code_corpus(offending)
