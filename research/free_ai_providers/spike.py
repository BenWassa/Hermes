"""Isolated, opt-in non-Gemini Hermes editorial API probe (issue #77).

Only accepts a pre-existing #72-style fixture/export. Never imports or modifies
the production pipeline. Uses Python stdlib and does not persist model prose.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

MODELS = {
    "zai": ("glm-4.7-flash", "ZAI_API_KEY",
            "https://api.z.ai/api/paas/v4/chat/completions"),
    "groq": ("openai/gpt-oss-120b", "GROQ_API_KEY",
             "https://api.groq.com/openai/v1/chat/completions"),
    "openrouter": ("nvidia/nemotron-3-ultra-550b-a55b:free",
                   "OPENROUTER_API_KEY",
                   "https://openrouter.ai/api/v1/chat/completions"),
    "mistral": ("mistral-small-2603", "MISTRAL_API_KEY",
               "https://api.mistral.ai/v1/chat/completions"),
    "cloudflare": ("@cf/zai-org/glm-4.7-flash", "CLOUDFLARE_API_TOKEN", ""),
}
RATE_HEADERS = ("retry-after", "x-ratelimit-limit-requests",
                "x-ratelimit-remaining-requests", "x-ratelimit-limit-tokens",
                "x-ratelimit-remaining-tokens", "x-ratelimit-reset-tokens")


def messages_and_counts(fixture: dict) -> tuple[list[dict], dict]:
    """Accept #72 message exports or a literal Hermes system/user payload."""
    src = fixture.get("request") or fixture
    if isinstance(src.get("messages"), list):
        messages = src["messages"]
    else:
        system = src.get("system_instruction")
        user = src.get("user_content", src.get("contents"))
        if not isinstance(system, str) or not isinstance(user, (str, list, dict)):
            raise ValueError("Fixture needs messages or system_instruction + user_content")
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(user, ensure_ascii=False)
                     if not isinstance(user, str) else user}]
    if not messages or any(
        not isinstance(m, dict) or m.get("role") not in ("system", "user", "assistant")
        or not isinstance(m.get("content"), str) for m in messages
    ):
        raise ValueError("Fixture messages must be role/content strings")
    user = next((m["content"] for m in reversed(messages)
                 if m["role"] == "user"), "")
    try:
        obj = json.loads(user)
    except (ValueError, TypeError):
        obj = None
    if isinstance(obj, list):
        stories, following = obj, []
    elif isinstance(obj, dict):
        stories, following = obj.get("stories", []), obj.get("following", [])
    else:
        stories, following = [], []
    if not isinstance(stories, list) or not isinstance(following, list):
        raise ValueError("stories and following must be lists")
    keys = [str(x.get("key")) for x in following if isinstance(x, dict)
            and x.get("key") is not None]
    return messages, {"stories": len(stories), "following": len(following),
                      "following_keys": keys,
                      "input_utf8_bytes": len(json.dumps(messages, ensure_ascii=False).encode())}


def validate_hermes(output: object, expected_keys: list[str]) -> dict:
    """Transport/structural check, not #72's editorial accuracy rubric."""
    sections = output.get("sections") if isinstance(output, dict) else None
    shape_ok = isinstance(sections, list) and all(
        isinstance(section, dict) and isinstance(section.get("id"), str)
        and isinstance(section.get("stories"), list) for section in sections
    )
    following = output.get("following", []) if isinstance(output, dict) else []
    got = [x.get("key") for x in following if isinstance(x, dict)] \
        if isinstance(following, list) else []
    return {"sections_shape_valid": bool(shape_ok),
            "following_keys_exact": (got == expected_keys) if expected_keys else None,
            "section_count": len(sections) if isinstance(sections, list) else None}


def endpoint_for(provider: str) -> str:
    if provider != "cloudflare":
        return MODELS[provider][2]
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    if not account or not all(c.isalnum() or c in "-_" for c in account):
        raise ValueError("CLOUDFLARE_ACCOUNT_ID missing or invalid")
    return ("https://api.cloudflare.com/client/v4/accounts/"
            + account + "/ai/v1/chat/completions")


def probe(fixture: dict, provider: str, model: str | None = None,
          max_tokens: int = 16000, live: bool = False,
          json_mode: bool = False, timeout: int = 240,
          require_full_size: bool = False) -> dict:
    if provider not in MODELS:
        raise ValueError("Unsupported provider")
    if not 1 <= max_tokens <= 16000:
        raise ValueError("max_tokens must be between 1 and Hermes' 16000 ceiling")
    messages, counts = messages_and_counts(fixture)
    if require_full_size and not (counts["stories"] == 60 and counts["following"] > 0):
        raise ValueError("Full-size test requires 60 stories and >=1 Following seed")
    default_model, key_name, _ = MODELS[provider]
    model = model or default_model
    result = {"fixture_id": str(fixture.get("fixture_id", "unlabelled")),
              "provider": provider, "model": model,
              "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "requested_output_cap": max_tokens,
              "requested_json_mode": json_mode,
              "story_count": counts["stories"],
              "following_count": counts["following"],
              "input_utf8_bytes": counts["input_utf8_bytes"],
              "status": "preflight_only", "live": False}
    if not live:
        result["credential_present"] = bool(os.environ.get(key_name))
        return result
    key = os.environ.get(key_name)
    if not key:
        result["status"] = "missing_credentials"
        return result
    url = endpoint_for(provider)
    body = {"model": model, "messages": messages, "max_tokens": max_tokens,
            "temperature": 0.3, "stream": False}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(
        url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"},
        method="POST")
    start = time.monotonic()
    result["live"] = True
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            response_headers = response.headers
            status_code = response.status
    except urllib.error.HTTPError as exc:
        result.update({"status": "http_error", "http_status": exc.code,
                       "latency_seconds": round(time.monotonic() - start, 3),
                       "rate_headers": {k: exc.headers[k] for k in RATE_HEADERS
                                        if k in exc.headers}})
        return result
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        result.update({"status": "network_error",
                       "exception_type": type(exc).__name__,
                       "latency_seconds": round(time.monotonic() - start, 3)})
        return result
    result.update({"http_status": status_code,
                   "latency_seconds": round(time.monotonic() - start, 3),
                   "response_sha256": hashlib.sha256(raw).hexdigest(),
                   "rate_headers": {k: response_headers[k] for k in RATE_HEADERS
                                    if k in response_headers}})
    try:
        response_obj = json.loads(raw)
        choice = response_obj["choices"][0]
        message = choice["message"]["content"]
        result["finish_reason"] = choice.get("finish_reason")
        result["usage"] = response_obj.get("usage", {})
        edition = json.loads(message)
        result.update(validate_hermes(edition, counts["following_keys"]))
        result["status"] = "valid_json" if result["sections_shape_valid"] and (
            result["following_keys_exact"] is not False) else "invalid_hermes_shape"
    except (ValueError, TypeError, KeyError, IndexError):
        result["status"] = "invalid_json_or_response"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--provider", choices=sorted(MODELS), required=True)
    parser.add_argument("--model", help="Explicit pinned model slug")
    parser.add_argument("--max-output-tokens", type=int, default=16000)
    parser.add_argument("--json-mode", action="store_true",
                        help="Opt into JSON mode only after verifying model support")
    parser.add_argument("--require-full-size", action="store_true")
    parser.add_argument("--live", action="store_true",
                        help="Explicitly authorize one API request; never auto-retry")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--result", type=Path, help="Write metrics only, never model text")
    args = parser.parse_args(argv)
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    result = probe(fixture, args.provider, args.model,
                   args.max_output_tokens, args.live, args.json_mode,
                   args.timeout, args.require_full_size)
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.result:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if result["status"] not in (
        "missing_credentials", "http_error", "network_error",
        "invalid_json_or_response", "invalid_hermes_shape") else 2


if __name__ == "__main__":
    sys.exit(main())
