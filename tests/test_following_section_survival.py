"""Following must remain reachable even when editorial Opinion is empty."""

from src.curate import _ensure_opinion_section


def test_empty_editorial_opinion_is_inserted_in_canonical_section_order():
    sections = [
        {"id": "front", "label": "Front", "stories": [{}]},
        {"id": "toronto", "label": "Toronto", "stories": [{}]},
        {"id": "world", "label": "World", "stories": [{}]},
        {"id": "sports", "label": "Sports", "stories": [{}]},
        {"id": "business", "label": "Business", "stories": [{}]},
    ]

    _ensure_opinion_section(sections)

    assert [section["id"] for section in sections] == [
        "front", "toronto", "world", "sports", "business", "opinion"
    ]
    assert sections[-1] == {"id": "opinion", "label": "Opinion", "stories": []}


def test_existing_editorial_opinion_is_not_duplicated_or_rewritten():
    opinion = {"id": "opinion", "label": "Opinion", "stories": [{"id": "o1"}]}
    sections = [
        {"id": "front", "label": "Front", "stories": [{}]},
        opinion,
    ]

    returned = _ensure_opinion_section(sections)

    assert returned is sections
    assert [section["id"] for section in sections].count("opinion") == 1
    assert sections[-1] is opinion
