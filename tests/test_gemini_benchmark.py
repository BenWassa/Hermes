"""Offline contract tests for research/gemini_benchmark.py; no API credentials or network."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from research import gemini_benchmark as b


def test_fixture_contract_and_diversity():
    cases = b.read_fixtures()["cases"]
    assert len(cases) >= 10
    assert len({c["id"] for c in cases}) == len(cases)
    assert all(c["origin"] == "synthetic_public_metadata_hypothetical" for c in cases)
    assert sum(bool(c.get("following")) for c in cases) > 0
    assert any(len(c["stories"]) > 60 for c in cases)
    assert any(c["date"] == "2026-09-12" for c in cases)


def test_fixture_invalid_reference_rejected(tmp_path):
    fixture = b.read_fixtures()
    fixture["cases"][0]["reference"]["must_select"] = ["https://example.org/not-in-input"]
    path = tmp_path / "broken.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(ValueError, match="outside input"):
        b.read_fixtures(path)


def test_current_production_request_boundary():
    cases = {c["id"]: c for c in b.read_fixtures()["cases"]}
    prompt, payload = b.request_payload(cases["dense-sixty-cap"])
    stories = json.loads(payload)
    assert len(stories) == 60
    assert all(set(s).issubset(set(b.CURATION_KEYS) | {"editorial_priority"}) for s in stories)
    assert any("Ottawa announces" in x["title"] for x in stories)
    assert "CANADA-NATIONAL EDITORIAL PRIORITY" in prompt


def test_following_payload_preserves_separate_authority():
    case = next(c for c in b.read_fixtures()["cases"] if c["id"] == "opinion-following")
    prompt, payload = b.request_payload(case)
    actual = json.loads(payload)
    assert isinstance(actual, dict)
    assert len(actual["following"]) == 2
    assert list(actual["following"][0]) == list(b.FOLLOWING_KEYS)
    assert "FOLLOWING OVERRIDE" in prompt
    assert "sports" not in [s["section_hint"] for s in actual["stories"]]


def sample_story(link, lead=True, analysis="An insight."):
    return {"id": "f1", "lead": lead, "headline": "A headline",
            "summary": "Source-grounded news summary.", "analysis": analysis,
            "sensitivity": False, "image": None, "link": link}


def test_schema_valid_and_reference_scores():
    case = next(c for c in b.read_fixtures()["cases"] if c["id"] == "canada-crowded")
    story = sample_story(case["reference"]["must_select"][0])
    story["summary"] = "A $18 billion policy was announced."
    out = b.validate_output(case, {"sections": [
        {"id": "front", "label": "Front Page", "stories": [story]}]})
    assert out["schema_ok"]
    assert out["metrics"]["must_select"] == [1, 2]
    assert out["metrics"]["literal_fact_anchors_conditional"] == [1, 1]


def test_rejects_unattributed_link_multiple_leads_and_nonlead_analysis():
    case = b.read_fixtures()["cases"][0]
    story = sample_story("https://example.org/invented")
    second = sample_story(case["stories"][0]["link"], False, "Improper analysis")
    second["id"] = "f2"
    out = b.validate_output(case, {"sections": [
        {"id": "front", "label": "Front Page", "stories": [story, second]}]})
    assert not out["schema_ok"]
    assert any("unattributed" in x for x in out["issues"])
    assert any("non-lead analysis" in x for x in out["issues"])


def test_following_keys_must_be_exact_and_ordered():
    case = next(c for c in b.read_fixtures()["cases"] if c["id"] == "opinion-following")
    out = b.validate_output(case, {"sections": [], "following": [
        {"key": "voice-key-02", "summary": "Reversed.", "sensitivity": False},
        {"key": "voice-key-01", "summary": "Reversed.", "sensitivity": False}]})
    assert not out["schema_ok"]
    assert any("Following" in x for x in out["issues"])


def test_variant_settings_and_prices():
    assert b.variant("gemini-2.5-flash@default") == ("gemini-2.5-flash", None)
    assert b.variant("gemini-3.8-flash@high") == ("gemini-3.8-flash", "high")
    with pytest.raises(ValueError):
        b.variant("gemini-3.8-flash@minimal")
    assert b.price("gemini-3.8-flash", 12500, 4800, 1200, "intro_2026") == 0.031875
    assert b.price("gemini-3.8-flash", 12500, 4800, 1200, "standard_2027") == 0.06375
    assert b.price("gemini-3.8-flash", 12500, 4800, None, "standard_2027") is None


def test_offline_run_is_zero_calls(monkeypatch, capsys):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert b.main(["plan", "--fixture", "quiet-cycle", "--repeat", "2"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["planned_calls"] == 8
    assert output["api_calls"] == 0


def test_live_guard_requires_explicit_consent(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="both --live and --confirm-spend"):
        b.main(["run", "--live", "--fixture", "quiet-cycle", "--repeat", "1"])
    with pytest.raises(SystemExit, match="No GEMINI_API_KEY"):
        b.main(["run", "--live", "--confirm-spend", "--fixture", "quiet-cycle", "--repeat", "1"])


def test_summarize_empty_and_recorded_errors(tmp_path):
    assert b.summarize(tmp_path) == {"runs": 0, "variants": {}}
    record = {"fixture_id": "quiet-cycle", "model": "gemini-2.5-flash",
              "thinking_level": None, "trial": 1, "status": "invalid_json",
              "latency_seconds": 2.5, "validation": {"schema_ok": False},
              "usd_intro_2026": .01, "usd_2027": .01}
    (tmp_path / "fixture.json").write_text(json.dumps(record), encoding="utf-8")
    data = b.summarize(tmp_path)
    assert data["runs"] == 1
    assert data["variants"]["gemini-2.5-flash@default"]["ok"] == 0
    assert data["variants"]["gemini-2.5-flash@default"]["errors"] == {"invalid_json": 1}


def test_usage_missing_tokens_is_not_zero():
    result = b.safe_usage(SimpleNamespace(usage_metadata=SimpleNamespace(
        prompt_token_count=200, candidates_token_count=50, total_token_count=300)))
    assert result["thought_tokens"] is None
    assert result["input_tokens"] == 200
