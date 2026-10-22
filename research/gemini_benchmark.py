"""Opt-in, non-production Hermes Gemini editorial benchmark (#72).

Fixtures use normalized public/synthetic metadata, never publisher bodies.
No model API calls occur unless both --live and --confirm-spend are passed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import time

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = ROOT / "research" / "gemini" / "fixtures.json"
DEFAULT_RUNS = ROOT / "research" / "gemini" / "runs"
SECTION_CAPS = {"front": 5, "toronto": 4, "world": 4, "business": 4, "opinion": 4}
CURATION_KEYS = ("title", "description", "source", "section_hint", "pub_date", "image", "link")
FOLLOWING_KEYS = ("key", "headline", "description", "author", "publication", "published_at", "link")
MODELS = {
    "gemini-2.5-flash": (None,),
    "gemini-3.8-flash": ("low", "medium", "high"),
    "gemini-3.5-flash-lite": ("minimal",),
    "gemini-4-argon": ("medium",),
    "gemini-3.1-pro-preview": ("high",),
}
DEFAULT_VARIANTS = ("gemini-2.5-flash@default", "gemini-3.8-flash@low",
                    "gemini-3.8-flash@medium", "gemini-3.8-flash@high")
# USD/1M: standard synchronous text input, output INCLUDING thought tokens.
# Snapshotted 2026-10-22: https://ai.google.dev/gemini-api/docs/pricing
PRICES = {
    "gemini-2.5-flash": ((.30, 2.50), (.30, 2.50)),
    "gemini-3.8-flash": ((.75, 3.75), (1.50, 7.50)),
    "gemini-3.5-flash-lite": ((.30, 2.50), (.30, 2.50)),
    "gemini-4-argon": ((2.00, 10.00), (4.00, 20.00)),
    "gemini-3.1-pro-preview": ((2.00, 12.00), (2.00, 12.00)),
}


def stable_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(obj: object) -> str:
    return hashlib.sha256(stable_json(obj).encode("utf-8")).hexdigest()


def read_fixtures(path: Path = DEFAULT_FIXTURES) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("cases"), list):
        raise ValueError("Expected benchmark fixture schema_version=1 with cases array")
    seen = set()
    for case in data["cases"]:
        name = case["id"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name) or name in seen:
            raise ValueError(f"Invalid or duplicate fixture id: {name}")
        seen.add(name)
        dt.date.fromisoformat(case["date"])
        stories = case["stories"]
        if not stories or len(stories) > 100:
            raise ValueError(f"{name}: expected 1..100 normalized candidate stories")
        links = [s.get("link") for s in stories]
        if any(not isinstance(link, str) or not link.startswith("https://") for link in links):
            raise ValueError(f"{name}: every input requires an https source link")
        if len(set(links)) != len(links):
            raise ValueError(f"{name}: candidate URLs must be unique; use duplicate_groups for event overlap")
        for story in stories:
            if not all(k in story for k in CURATION_KEYS):
                raise ValueError(f"{name}: story missing a production curation field")
        following = case.get("following", [])
        keys = [f.get("key") for f in following]
        if len(set(keys)) != len(keys) or any(not k for k in keys):
            raise ValueError(f"{name}: Following keys must be unique and nonempty")
        for f in following:
            if not all(k in f for k in FOLLOWING_KEYS):
                raise ValueError(f"{name}: Following metadata incomplete")
        ref = case.get("reference", {})
        for key in ("must_select", "must_omit"):
            if not set(ref.get(key, [])).issubset(links):
                raise ValueError(f"{name}: {key} has URL outside input")
        if not set(ref.get("section_by_link", {})).issubset(links):
            raise ValueError(f"{name}: section_by_link has URL outside input")
        if any(section not in SECTION_CAPS for section in ref.get("section_by_link", {}).values()):
            raise ValueError(f"{name}: invalid reference section")
        if any(not set(group).issubset(links) for group in ref.get("duplicate_groups", [])):
            raise ValueError(f"{name}: duplicate_groups has URL outside input")
        if any(not set(pair).issubset(links) or len(pair) != 2 for pair in ref.get("ranking_pairs", [])):
            raise ValueError(f"{name}: invalid ranking_pairs")
        if any(fact.get("link") not in links or not fact.get("text") for fact in ref.get("facts", [])):
            raise ValueError(f"{name}: invalid fact anchor")
    return data


def variant(spec: str) -> tuple[str, str | None]:
    model, sep, level = spec.partition("@")
    if not sep:
        level = "default" if model == "gemini-2.5-flash" else "medium"
    level = None if level == "default" else level
    if model not in MODELS or level not in MODELS[model]:
        raise ValueError(f"Unsupported variant {spec}; use explicit model@level")
    return model, level


def request_payload(case: dict) -> tuple[str, str]:
    """Use the exact current production trim, model projection and prompt."""
    from src import canada, config, curate
    from src.opinion import curation_following_view
    today = dt.date.fromisoformat(case["date"])
    stories = curate._trim_input(case["stories"], today=today)
    following = case.get("following", [])
    body = ({"stories": curate._curation_view(stories, today),
             "following": curation_following_view(following)}
            if following else curate._curation_view(stories, today))
    prompt = config.build_curate_system_prompt(today) + canada.editorial_instruction(today)
    if following:
        prompt += curate._FOLLOWING_INSTRUCTION
    return prompt, json.dumps(body, ensure_ascii=False)


def validate_output(case: dict, raw: object) -> dict:
    """Deterministic structural/proxy checks; NOT a factual accuracy judgment."""
    issues = []
    if not isinstance(raw, dict) or not isinstance(raw.get("sections"), list):
        return {"schema_ok": False, "issues": ["missing sections array"], "metrics": {}}
    sections = raw["sections"]
    seen_section = set()
    seen_ids = set()
    used_links = []
    loc = {}
    expected_order = list(SECTION_CAPS)
    for s in sections:
        if not isinstance(s, dict):
            issues.append("non-object section")
            continue
        sid = s.get("id")
        if sid not in SECTION_CAPS or sid in seen_section:
            issues.append(f"invalid/duplicate section {sid}")
            continue
        seen_section.add(sid)
        if s.get("label") not in (None, {"front": "Front Page", "toronto": "Toronto", "world": "World", "business": "Business", "opinion": "Opinion"}[sid]):
            issues.append(f"section label mismatch {sid}")
        stories = s.get("stories")
        if not isinstance(stories, list):
            issues.append(f"invalid stories array {sid}")
            continue
        if len(stories) > SECTION_CAPS[sid]:
            issues.append(f"over cap {sid}")
        leads = 0
        for rank, item in enumerate(stories):
            if not isinstance(item, dict):
                issues.append(f"non-object story {sid}")
                continue
            required = ("id", "lead", "headline", "summary", "analysis", "sensitivity", "link", "image")
            if any(k not in item for k in required):
                issues.append(f"missing story fields {sid}/{rank}")
            if not isinstance(item.get("lead"), bool) or not isinstance(item.get("sensitivity"), bool):
                issues.append(f"invalid booleans {sid}/{rank}")
            leads += item.get("lead") is True
            item_id = item.get("id")
            if not isinstance(item_id, str) or item_id in seen_ids:
                issues.append(f"bad/duplicate story id {item_id}")
            seen_ids.add(item_id)
            if not isinstance(item.get("summary"), str) or not item.get("summary", "").strip():
                issues.append(f"missing summary {sid}/{rank}")
            if item.get("lead") is not True and item.get("analysis") not in (None, ""):
                issues.append(f"non-lead analysis {sid}/{rank}")
            if item.get("analysis") not in (None, "") and not isinstance(item.get("analysis"), str):
                issues.append(f"invalid analysis {sid}/{rank}")
            link = item.get("link")
            if not isinstance(link, str):
                issues.append(f"invalid link {sid}/{rank}")
                continue
            used_links.append(link)
            if link in loc:
                issues.append(f"duplicate link {link}")
            loc[link] = (sid, rank, item)
        if stories and leads != 1:
            issues.append(f"expected one lead {sid}")
    if [s.get("id") for s in sections if isinstance(s, dict)] != [x for x in expected_order if x in seen_section]:
        issues.append("noncanonical section order")
    input_by_link = {x["link"]: x for x in case["stories"]}
    for link in used_links:
        if link not in input_by_link:
            issues.append(f"unattributed source link {link}")
        elif loc[link][2].get("image") != input_by_link[link]["image"]:
            issues.append(f"image not preserved {link}")
    following = case.get("following", [])
    if following:
        returned = raw.get("following")
        if not isinstance(returned, list) or [x.get("key") for x in returned if isinstance(x, dict)] != [x["key"] for x in following]:
            issues.append("Following key/order/coverage mismatch")
        else:
            for item in returned:
                if not isinstance(item.get("summary"), str) or not item["summary"].strip() or not isinstance(item.get("sensitivity"), bool):
                    issues.append("invalid Following summary or sensitivity")
    ref = case.get("reference", {})
    required = ref.get("must_select", [])
    omitted = ref.get("must_omit", [])
    recall = sum(x in loc for x in required)
    omit_success = sum(x not in loc for x in omitted)
    section_expectations = ref.get("section_by_link", {})
    section_correct = sum(x in loc and loc[x][0] == expected for x, expected in section_expectations.items())
    groups = ref.get("duplicate_groups", [])
    duplicate_success = sum(sum(x in loc for x in group) <= 1 for group in groups)
    pairs = ref.get("ranking_pairs", [])
    ranking_observed = [(a, b) for a, b in pairs if a in loc and b in loc]
    ranking_correct = sum(
        (expected_order.index(loc[a][0]), loc[a][1]) < (expected_order.index(loc[b][0]), loc[b][1])
        for a, b in ranking_observed
    )
    # Exact anchored excerpts are conservative red flags; human adjudication still required.
    facts = ref.get("facts", [])
    fact_hits = 0
    for fact in facts:
        if fact["link"] not in loc:
            continue
        item = loc[fact["link"]][2]
        text = " ".join(str(item.get(k) or "") for k in ("headline", "sub", "summary", "analysis"))
        fact_hits += fact["text"].casefold() in text.casefold()
    metrics = {
        "must_select": [recall, len(required)], "must_omit": [omit_success, len(omitted)],
        "section_placement": [section_correct, len(section_expectations)],
        "dedupe_groups": [duplicate_success, len(groups)],
        "ranking_pairs_conditional": [ranking_correct, len(ranking_observed)],
        "ranking_pairs_total": len(pairs),
        "literal_fact_anchors_conditional": [fact_hits, sum(f["link"] in loc for f in facts)],
        "selected_count": len(used_links),
    }
    return {"schema_ok": not issues, "issues": issues, "metrics": metrics}


def price(model: str, prompt_tokens: int | None, visible_tokens: int | None,
          thought_tokens: int | None, period: str) -> float | None:
    if prompt_tokens is None or visible_tokens is None or thought_tokens is None:
        return None
    i, o = PRICES[model][0 if period == "intro_2026" else 1]
    return round((prompt_tokens * i + (visible_tokens + thought_tokens) * o) / 1_000_000, 8)


def safe_usage(resp) -> dict:
    usage = getattr(resp, "usage_metadata", None)
    def value(key):
        v = getattr(usage, key, None)
        return int(v) if v is not None else None
    return {"input_tokens": value("prompt_token_count"),
            "visible_output_tokens": value("candidates_token_count"),
            "thought_tokens": value("thoughts_token_count"),
            "total_tokens": value("total_token_count")}


def run(args) -> None:
    fixtures = read_fixtures(args.fixtures)
    cases = [c for c in fixtures["cases"] if not args.fixture or c["id"] in args.fixture]
    if not cases:
        raise SystemExit("No fixtures selected")
    specs = [v.strip() for v in args.models.split(",")]
    variants = [(s, *variant(s)) for s in specs]
    count = len(cases) * len(variants) * args.repeat
    if count > args.max_calls:
        raise SystemExit(f"Refusing {count} calls (max {args.max_calls}); narrow selection deliberately")
    if not args.live:
        print(json.dumps({"mode": "offline_plan", "fixtures": len(cases), "variants": specs,
                          "repetitions": args.repeat, "planned_calls": count,
                          "fixture_hash": digest(fixtures), "api_calls": 0}, indent=2))
        return
    if not args.confirm_spend:
        raise SystemExit("Live calls require both --live and --confirm-spend")
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("No GEMINI_API_KEY/GOOGLE_API_KEY in this environment; 0 API calls made")
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=key)
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": 1, "fixture_hash": digest(fixtures),
                "variants": specs, "repeat": args.repeat, "max_output_tokens": args.max_output_tokens,
                "sdk": "google-genai", "recorded_at_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    (args.out / "manifest.json").write_text(stable_json(manifest) + "\n", encoding="utf-8")
    for case in cases:
        prompt, payload = request_payload(case)
        for spec, model, level in variants:
            for trial in range(1, args.repeat + 1):
                dest = args.out / f"{case['id']}__{model}__{level or 'default'}__{trial}.json"
                if dest.exists() and not args.overwrite:
                    raise SystemExit(f"{dest} already exists; refuse silent overwrite")
                params = {"system_instruction": prompt, "response_mime_type": "application/json",
                          "temperature": 0.3, "max_output_tokens": args.max_output_tokens}
                if model == "gemini-2.5-flash":
                    params["thinking_config"] = types.ThinkingConfig(thinking_budget=1024)
                else:
                    params["thinking_config"] = types.ThinkingConfig(thinking_level=level)
                record = {"schema_version": 1, "fixture_id": case["id"], "fixture_hash": digest(case),
                          "model": model, "thinking_level": level, "trial": trial,
                          "system_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                          "payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                          "payload": json.loads(payload), "prompt": prompt,
                          "max_output_tokens": args.max_output_tokens,
                          "temperature": .3, "status": "error", "latency_seconds": None}
                start = time.perf_counter()
                try:
                    resp = client.models.generate_content(
                        model=model, contents=payload, config=types.GenerateContentConfig(**params))
                    record["latency_seconds"] = round(time.perf_counter() - start, 3)
                    record["usage"] = safe_usage(resp)
                    record["raw_output"] = resp.text or ""
                    record["finish_reason"] = str(getattr(resp.candidates[0], "finish_reason", "")) if resp.candidates else None
                    try:
                        parsed = json.loads(record["raw_output"])
                    except (ValueError, TypeError) as exc:
                        record["status"] = "invalid_json"
                        record["validation"] = {"schema_ok": False, "issues": [str(exc)]}
                    else:
                        record["status"] = "ok"
                        record["validation"] = validate_output(case, parsed)
                    u = record["usage"]
                    record["usd_intro_2026"] = price(model, u["input_tokens"], u["visible_output_tokens"], u["thought_tokens"], "intro_2026")
                    record["usd_2027"] = price(model, u["input_tokens"], u["visible_output_tokens"], u["thought_tokens"], "standard_2027")
                except Exception as exc:  # keep failures as measured, no retry
                    record["latency_seconds"] = round(time.perf_counter() - start, 3)
                    record["error_type"] = type(exc).__name__
                    record["error_code"] = getattr(exc, "code", None)
                    # Deliberately do not store exception message (may include request/key).
                dest.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(f"{dest.name}: {record['status']} in {record['latency_seconds']}s")
                if args.pause_seconds and (case is not cases[-1] or trial < args.repeat):
                    time.sleep(args.pause_seconds)


def summarize(folder: Path) -> dict:
    """Summarize *recorded* runs only; do not fill missing trials or claim semantic accuracy."""
    from itertools import combinations
    import math

    records = []
    for path in sorted(folder.glob("*.json")):
        if path.name == "manifest.json":
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if "fixture_id" in doc and "model" in doc:
            records.append(doc)
    result = {"runs": len(records), "variants": {}}
    proxy_names = ("must_select", "must_omit", "section_placement", "dedupe_groups",
                   "ranking_pairs_conditional", "literal_fact_anchors_conditional")
    for rec in records:
        name = rec["model"] + "@" + (rec["thinking_level"] or "default")
        group = result["variants"].setdefault(name, {
            "runs": 0, "ok": 0, "valid_schema": 0, "latencies": [],
            "cost_intro": [], "cost_2027": [], "errors": {}, "tokens": {},
            "proxies": {key: [0, 0] for key in proxy_names}, "selections": {},
            "max_output_budgets": set(), "prompt_fingerprints": set(),
            "issue_counts": {},
        })
        group["runs"] += 1
        group["ok"] += rec["status"] == "ok"
        group["valid_schema"] += bool(rec.get("validation", {}).get("schema_ok"))
        if rec.get("latency_seconds") is not None:
            group["latencies"].append(rec["latency_seconds"])
        for source, target in (("usd_intro_2026", "cost_intro"), ("usd_2027", "cost_2027")):
            if rec.get(source) is not None:
                group[target].append(rec[source])
        if rec["status"] != "ok":
            group["errors"][rec["status"]] = group["errors"].get(rec["status"], 0) + 1
        if rec.get("max_output_tokens"):
            group["max_output_budgets"].add(rec["max_output_tokens"])
        if rec.get("system_prompt_sha256"):
            group["prompt_fingerprints"].add(rec["system_prompt_sha256"])
        for key, val in rec.get("usage", {}).items():
            if val is not None:
                group["tokens"].setdefault(key, []).append(val)
        check = rec.get("validation", {})
        for issue in check.get("issues", []):
            category = issue.split(" ", 1)[0]
            group["issue_counts"][category] = group["issue_counts"].get(category, 0) + 1
        for key in proxy_names:
            score = check.get("metrics", {}).get(key)
            if isinstance(score, list) and len(score) == 2:
                group["proxies"][key][0] += score[0]
                group["proxies"][key][1] += score[1]
        if rec.get("status") == "ok":
            try:
                output = json.loads(rec["raw_output"])
                links = {item["link"] for section in output["sections"]
                         for item in section.get("stories", []) if isinstance(item.get("link"), str)}
            except (AttributeError, KeyError, TypeError, ValueError):
                continue
            group["selections"].setdefault(rec["fixture_id"], []).append(links)
    for group in result["variants"].values():
        times = sorted(group.pop("latencies"))
        group["p50_latency_seconds"] = round(statistics.median(times), 6) if times else None
        group["p95_latency_seconds"] = round(times[math.ceil(len(times) * .95) - 1], 6) if times else None
        for key, destination in (("cost_intro", "mean_usd_intro"), ("cost_2027", "mean_usd_2027")):
            values = group.pop(key)
            group[destination] = round(statistics.mean(values), 8) if values else None
            group[destination + "_sample_n"] = len(values)
        group["mean_tokens"] = {k: round(statistics.mean(v), 1) for k, v in group.pop("tokens").items()}
        for key, score in group["proxies"].items():
            group["proxies"][key] = {"passed": score[0], "eligible": score[1],
                                     "rate": round(score[0] / score[1], 4) if score[1] else None}
        sets_by_case = group.pop("selections")
        comparisons = []
        for selections in sets_by_case.values():
            for a, b in combinations(selections, 2):
                comparisons.append(len(a & b) / len(a | b) if (a | b) else 1.0)
        group["repeat_jaccard_mean"] = round(statistics.mean(comparisons), 4) if comparisons else None
        group["repeat_pairs"] = len(comparisons)
        group["max_output_budgets"] = sorted(group["max_output_budgets"])
        group["prompt_fingerprint_count"] = len(group.pop("prompt_fingerprints"))
        group["note"] = "Automatic proxies only; manual blind factual and analysis review required"
    return result


def blind(folder: Path, dest: Path) -> None:
    """Create reviewer packet and SEPARATE private key; never label packet by model."""
    rows = []
    for path in sorted(folder.glob("*.json")):
        if path.name == "manifest.json":
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("status") in ("ok", "invalid_json"):
            rows.append(record)
    if not rows:
        raise SystemExit("No recorded outputs to blind")
    import secrets
    salt = secrets.token_hex(12)
    packets = []
    key = {}
    for rec in rows:
        token = hashlib.sha256((salt + stable_json([rec["fixture_id"], rec["model"],
                      rec["thinking_level"], rec["trial"]])).encode()).hexdigest()[:16]
        packets.append({"review_id": token, "fixture_id": rec["fixture_id"],
                        "raw_output": rec.get("raw_output", "")})
        key[token] = {"model": rec["model"], "thinking_level": rec["thinking_level"],
                      "trial": rec["trial"], "fixture_id": rec["fixture_id"]}
    packets.sort(key=lambda x: x["review_id"])
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "review_packets.jsonl").write_text("".join(stable_json(x) + "\n" for x in packets), encoding="utf-8")
    (dest / "review_key.private.json").write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    print(f"Created {len(packets)} blinded packets; keep review_key.private.json from reviewers.")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("validate", "plan", "run", "summarize", "blind"))
    p.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    p.add_argument("--out", type=Path, default=DEFAULT_RUNS)
    p.add_argument("--fixture", action="append", help="Select a fixture ID (repeatable)")
    p.add_argument("--models", default=",".join(DEFAULT_VARIANTS))
    p.add_argument("--repeat", type=int, default=2)
    p.add_argument("--max-calls", type=int, default=120)
    p.add_argument("--max-output-tokens", type=int, default=16000)
    p.add_argument("--live", action="store_true")
    p.add_argument("--confirm-spend", action="store_true")
    p.add_argument("--pause-seconds", type=float, default=5)
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--blind-out", type=Path, default=ROOT / "research" / "gemini" / "blind")
    args = p.parse_args(argv)
    if args.repeat < 1 or args.max_calls < 1 or not 1024 <= args.max_output_tokens <= 65536:
        p.error("repeat/max-calls must be positive; max-output-tokens must be 1024..65536")
    if args.command == "validate":
        cases = read_fixtures(args.fixtures)["cases"]
        print(f"Validated {len(cases)} benchmark fixtures")
    elif args.command in ("plan", "run"):
        if args.command == "plan":
            args.live = False
        run(args)
    elif args.command == "summarize":
        print(json.dumps(summarize(args.out), indent=2))
    else:
        blind(args.out, args.blind_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
