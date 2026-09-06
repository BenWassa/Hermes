"""Registry schema and validation."""

from __future__ import annotations

import json

import pytest

from src.voices.registry import RegistryError, load_registry, validate


def reg(**voice) -> dict:
    base = {"id": "a-writer", "name": "A Writer"}
    base.update(voice)
    return {"version": 1, "voices": [base]}


def problems_for(data) -> list[str]:
    _registry, problems = validate(data)
    return problems


def test_a_minimal_pool_attributed_voice_is_valid():
    assert problems_for(reg(byline_publications=["nytimes.com"])) == []


def test_duplicate_voice_ids_are_rejected():
    data = {"version": 1, "voices": [
        {"id": "x-y", "name": "Ex Why", "byline_publications": ["a.com"]},
        {"id": "x-y", "name": "Ex Why Two", "byline_publications": ["b.com"]},
    ]}
    assert any("duplicate voice id" in p for p in problems_for(data))


def test_empty_display_name_is_rejected():
    assert any("name must be a non-empty string" in p for p in problems_for(reg(name="   ")))


def test_a_display_name_that_is_not_a_person_is_rejected():
    assert any("does not parse as a person name" in p for p in problems_for(reg(name="Reuters")))


def test_unknown_adapter_type_is_rejected():
    data = reg(sources=[{"type": "carrier-pigeon", "authorship": "scope", "url": "https://x.com/f"}])
    assert any("not a known adapter" in p for p in problems_for(data))


def test_missing_required_source_field_is_rejected():
    data = reg(sources=[{"type": "guardian_contributor", "authorship": "provider_id"}])
    assert any("missing required field(s): tag" in p for p in problems_for(data))


def test_missing_authorship_mode_is_rejected():
    data = reg(sources=[{"type": "rss", "url": "https://x.com/feed"}])
    assert any("authorship is required" in p for p in problems_for(data))


def test_bad_authorship_mode_is_rejected():
    data = reg(sources=[{"type": "rss", "url": "https://x.com/feed", "authorship": "vibes"}])
    assert any("must be one of" in p for p in problems_for(data))


def test_non_absolute_source_url_is_rejected():
    data = reg(sources=[{"type": "rss", "url": "/feed", "authorship": "scope"}])
    assert any("not an absolute http(s) URL" in p for p in problems_for(data))


def test_redundant_duplicate_source_is_rejected():
    data = reg(sources=[
        {"id": "one", "type": "rss", "url": "https://x.com/feed", "authorship": "scope"},
        {"id": "two", "type": "rss", "url": "https://www.x.com/feed/", "authorship": "scope"},
    ])
    assert any("same source twice" in p for p in problems_for(data))


def test_enabled_voice_with_no_usable_source_is_rejected():
    assert any("no usable source or identity" in p for p in problems_for(reg()))


def test_a_dormant_voice_may_have_no_source():
    assert problems_for(reg(dormant=True)) == []


def test_two_voices_answering_to_one_byline_are_rejected():
    data = {"version": 1, "voices": [
        {"id": "smith-one", "name": "John Smith", "byline_publications": ["a.com"]},
        {"id": "smith-two", "name": "John Smith", "byline_publications": ["b.com"]},
    ]}
    assert any("claimed by more than one enabled voice" in p for p in problems_for(data))


def test_provider_id_only_voices_may_share_a_name():
    # Ambiguity is only a problem where a byline could decide it.
    data = {"version": 1, "voices": [
        {"id": "smith-one", "name": "John Smith", "require_evidence": "provider_id",
         "provider_ids": [{"provider": "guardian", "id": "profile/johnsmith1"}]},
        {"id": "smith-two", "name": "John Smith", "require_evidence": "provider_id",
         "provider_ids": [{"provider": "guardian", "id": "profile/johnsmith2"}]},
    ]}
    assert problems_for(data) == []


def test_one_provider_id_cannot_belong_to_two_people():
    data = {"version": 1, "voices": [
        {"id": "one", "name": "Person One", "provider_ids": [{"provider": "guardian", "id": "profile/x"}]},
        {"id": "two", "name": "Person Two", "provider_ids": [{"provider": "guardian", "id": "profile/X"}]},
    ]}
    assert any("claimed by more than one voice" in p for p in problems_for(data))


def test_strict_evidence_without_a_provider_id_is_rejected():
    data = reg(require_evidence="provider_id",
               sources=[{"type": "rss", "url": "https://x.com/feed", "authorship": "byline"}])
    assert any("can never attribute anything" in p for p in problems_for(data))


def test_disabling_a_broken_source_keeps_the_voice():
    data = reg(
        byline_publications=["nytimes.com"],
        sources=[{"id": "dead", "type": "rss", "url": "https://x.com/feed",
                  "authorship": "scope", "enabled": False}],
    )
    registry, problems = validate(data)
    assert problems == []
    voice = registry.voices[0]
    assert len(voice.sources) == 1 and voice.enabled_sources == ()


def test_unsupported_version_is_reported():
    assert any("unsupported registry version" in p for p in problems_for({"version": 99, "voices": []}))


def test_load_raises_on_missing_file():
    with pytest.raises(RegistryError):
        load_registry("does/not/exist.json")


def test_load_non_strict_tolerates_a_missing_file():
    assert load_registry("does/not/exist.json", strict=False).voices == ()


def test_malformed_json_fails_safely(tmp_path):
    path = tmp_path / "voices.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(RegistryError) as excinfo:
        load_registry(path)
    assert "not valid JSON" in str(excinfo.value)


def test_shipped_production_registry_is_valid(production_registry):
    assert production_registry.voices
    for voice in production_registry.voices:
        assert voice.alias_keys or voice.provider_id_keys


def test_shipped_notified_voices_have_a_watcher_source(production_registry):
    """Production `notify: true` must mean the watcher can actually discover work.

    A Voice may intentionally be morning-only by using pool attribution such as
    `byline_publications`, but the release-time watcher does not run the full
    morning fetch. Keep that distinction explicit in shipped configuration.
    """
    for voice in production_registry.active:
        if voice.notify:
            assert voice.enabled_sources, f"{voice.id} enables alerts but has no watcher source"


def test_shipped_registry_never_polls_a_source_twice(production_registry):
    keys = [source.key for voice in production_registry.active for source in voice.enabled_sources]
    assert len(keys) == len(set(keys))


def test_registry_file_is_pretty_json():
    raw = json.loads(open("data/voices.json", encoding="utf-8").read())
    assert raw["version"] == 1
