"""Deterministic tests for issue #77's opt-in transport spike."""
import json
from unittest import mock
import urllib.error

import pytest

from research.free_ai_providers.spike import (
    endpoint_for, messages_and_counts, probe, validate_hermes,
)


def fixture(n=60, following=2):
    return {
        "fixture_id": "contract-check",
        "system_instruction": "Return JSON sections and Following",
        "user_content": {
            "stories": [{"title": f"Test {i}", "description": "synthetic",
                         "link": f"https://example.org/{i}"} for i in range(n)],
            "following": [{"key": f"voice-{i}", "headline": "Synthetic"}
                          for i in range(following)],
        },
    }


def test_dry_run_never_uses_network():
    with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")):
        result = probe(fixture(), "groq", require_full_size=True)
    assert result["status"] == "preflight_only"
    assert result["story_count"] == 60
    assert result["following_count"] == 2
    assert result["requested_output_cap"] == 16000
    assert result["live"] is False


def test_fixture_messages_export_compatible():
    obj = fixture()
    messages = [{"role": "system", "content": obj["system_instruction"]},
                {"role": "user", "content": json.dumps(obj["user_content"])}]
    _, counts = messages_and_counts({"request": {"messages": messages}})
    assert counts["stories"] == 60
    assert counts["following_keys"] == ["voice-0", "voice-1"]


def test_reject_not_full_size():
    with pytest.raises(ValueError, match="60 stories"):
        probe(fixture(n=59), "zai", require_full_size=True)
    with pytest.raises(ValueError, match="Following"):
        probe(fixture(following=0), "zai", require_full_size=True)


def test_json_validity_is_not_editorial_quality():
    a = {"sections": [{"id": "front", "stories": []}],
         "following": [{"key": "voice-0"}, {"key": "voice-1"}]}
    assert validate_hermes(a, ["voice-0", "voice-1"])["sections_shape_valid"]
    assert validate_hermes(a, ["voice-1", "voice-0"])["following_keys_exact"] is False
    assert validate_hermes({"sections": {}}, [])["sections_shape_valid"] is False


def test_requires_credentials_without_request():
    with mock.patch.dict("os.environ", {"GROQ_API_KEY": ""}):
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            result = probe(fixture(), "groq", live=True)
    assert result["status"] == "missing_credentials"
    assert not result["live"]


def test_http_429_sanitizes_response():
    err = urllib.error.HTTPError("https://api.groq.com", 429,
                                 "hidden provider error with prompt", {"retry-after": "8"}, None)
    with mock.patch.dict("os.environ", {"GROQ_API_KEY": "test-only"}):
        with mock.patch("urllib.request.urlopen", side_effect=err):
            result = probe(fixture(), "groq", live=True)
    assert result["http_status"] == 429
    assert result["rate_headers"] == {"retry-after": "8"}
    assert "hidden" not in json.dumps(result)
    assert result["status"] == "http_error"


def test_cloudflare_requires_account_id():
    with mock.patch.dict("os.environ", {"CLOUDFLARE_ACCOUNT_ID": ""}):
        with pytest.raises(ValueError, match="CLOUDFLARE_ACCOUNT_ID"):
            endpoint_for("cloudflare")
    with mock.patch.dict("os.environ", {"CLOUDFLARE_ACCOUNT_ID": "abc123"}):
        assert endpoint_for("cloudflare").endswith(
            "/accounts/abc123/ai/v1/chat/completions")


def test_limits_and_invalid_fixture():
    with pytest.raises(ValueError, match="16000"):
        probe(fixture(), "mistral", max_tokens=16001)
    with pytest.raises(ValueError, match="messages"):
        messages_and_counts({"system_instruction": "x", "user_content": 2})
