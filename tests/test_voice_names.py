"""Name normalization and byline parsing.

These are the primitives every byline attribution rests on, so the cases that
matter most are the ones that must *not* match.
"""

from __future__ import annotations

import pytest

from src.voices.names import match_key, name_key, names_match, parse_byline


@pytest.mark.parametrize("left,right", [
    ("Jonathan Haidt", "jonathan haidt"),
    ("Jonathan Haidt", "  Jonathan   Haidt "),
    ("Zoë Beck", "Zoe Beck"),
    ("Jean-Luc Mounier", "Jean Luc Mounier"),
    ("Sean O'Brien", "Sean OBrien"),
    ("Dr. Jordan B. Peterson", "Jordan Peterson"),
    ("Conrad Black Jr.", "Conrad Black"),
    ("Jonathan D. Haidt", "Jonathan Haidt"),
])
def test_equivalent_spellings_match(left, right):
    assert names_match(left, right)


@pytest.mark.parametrize("left,right", [
    ("John Smith", "John Smyth"),
    ("John Smith", "Johnathan Smith"),
    ("Conrad Moffat Black", "Conrad Black"),      # a middle name is not an initial
    ("Jonathan Haidt", "Jon Haidt"),              # a nickname needs an explicit alias
    ("George Monbiot", "George Monbiot-Hughes"),
    ("Jane Doe", "Jane Doe Smith"),
    ("Haidt", "Jonathan Haidt"),                  # a mononym never matches
])
def test_distinct_names_do_not_match(left, right):
    assert not names_match(left, right)


@pytest.mark.parametrize("value", ["Reuters", "The Editorial Board", "Staff", "Guardian staff", ""])
def test_organisations_are_not_people(value):
    assert name_key(value) == ""
    assert match_key(value) == ""


@pytest.mark.parametrize("byline,expected", [
    ("By Jane Doe and John Roe", ["Jane Doe", "John Roe"]),
    ("Jonathan Haidt, Zach Rausch and Freya India", ["Jonathan Haidt", "Zach Rausch", "Freya India"]),
    ("By David Brooks", ["David Brooks"]),
    ("George Monbiot & Amelia Hargreaves", ["George Monbiot", "Amelia Hargreaves"]),
    ("Zach Rausch with Jonathan Haidt", ["Zach Rausch", "Jonathan Haidt"]),
    ("Patrick Wintour Diplomatic editor", ["Patrick Wintour"]),
    ("Jane Doe in Kyiv", ["Jane Doe"]),
    ("Jane Doe, Political Editor", ["Jane Doe"]),
])
def test_bylines_parse_to_people(byline, expected):
    assert parse_byline(byline) == expected


@pytest.mark.parametrize("byline", ["Reuters", "By The Editorial Board", "Staff", "", None, "Associated Press"])
def test_organisation_bylines_yield_no_people(byline):
    assert parse_byline(byline) == []


def test_coauthor_surnames_containing_and_are_not_split():
    assert parse_byline("Kim Anderson and Lee Grand") == ["Kim Anderson", "Lee Grand"]


def test_duplicate_names_in_one_byline_collapse():
    assert parse_byline("Jane Doe and Jane Doe") == ["Jane Doe"]
