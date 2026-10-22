"""Bounded, public-safe evidence for one published Daily edition.

Only observations and provider usage counters are retained. This module never
records prompts, raw model responses, article bodies, credentials or thoughts.
A failed evidence operation must never affect the published newspaper.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.metadata
import json
import logging
import os
import re
import tempfile
from collections import Counter, defaultdict
from contextvars import ContextVar
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from . import canada, config
from .voices.urls import canonical_url

log = logging.getLogger("the-daily.evidence")
SCHEMA_VERSION = 1
ROOT = Path("data/edition_evidence")
MAX_CANDIDATES = 240
MAX_BYTES = 131072
MAX_ATTEMPTS = 12
_ACTIVE: ContextVar["EditionEvidence | None"] = ContextVar("daily_evidence", default=None)
_SUSPICIOUS = re.compile(r"ignore (all |any )?(previous|prior)|system prompt|api.?key|secret|bearer |password|</?(script|system)", re.I)
_CONTROL = re.compile(r"[\x00-\x1f\x7f]+")
_SPACE = re.compile(r"\s+")


def _clean(value: object, limit: int) -> str:
    if not isinstance(value, (str, int, float)):
        return ""
    value = _SPACE.sub(" ", _CONTROL.sub(" ", str(value))).strip()
    if _SUSPICIOUS.search(value):
        return "[withheld]"
    return value[:limit]


def _public_url(value: object) -> str | None:
    """Store only bounded, credential-free canonical article locations."""
    url = canonical_url(value if isinstance(value, str) else "")
    if not url:
        return None
    parts = urlsplit(url)
    if parts.username or parts.password or parts.query or parts.fragment:
        # Query state may be required for provider identity but may contain
        # credentials. It stays in the SHA identity, not in the public record.
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    parts = urlsplit(url)
    if len(url) > 360 or re.search(r"(?:token|secret|apikey|api_key|auth|password|signature)", parts.path, re.I):
        return None
    return url


def _safe_source_id(value: object) -> str:
    """Keep ordinary public provider IDs, never embedded URL/query secrets."""
    if not isinstance(value, (str, int)):
        return ""
    raw = str(value).strip()
    if raw.startswith(("https://", "http://")):
        return _public_url(raw) or "[withheld]"
    if re.search(r"(?:token|api.?key|secret|auth|password|session|signature|[?&=])", raw, re.I):
        return "[withheld]"
    return _clean(raw, 100)


def _identity(story: dict) -> str:
    canonical = story.get("canonical_url") or canonical_url(story.get("link"))
    provider = _clean(story.get("provider"), 32)
    source_id = story.get("source_article_id")
    source = str(canonical or (f"{provider}:{source_id}" if source_id else story.get("link") or story.get("title") or "unknown"))
    return "a_" + hashlib.sha256(source.encode("utf-8", "replace")).hexdigest()[:20]


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _usage(response: object) -> dict:
    usage = getattr(response, "usage_metadata", None)
    fields = {
        "input_tokens": "prompt_token_count",
        "output_tokens": "candidates_token_count",
        "thinking_tokens": "thoughts_token_count",
        "total_tokens": "total_token_count",
        "cached_input_tokens": "cached_content_token_count",
    }
    result = {}
    for public, provider in fields.items():
        val = getattr(usage, provider, None)
        if isinstance(val, int) and not isinstance(val, bool) and val >= 0:
            result[public] = val
    return result


def current() -> "EditionEvidence | None":
    return _ACTIVE.get()


def activate(evidence: "EditionEvidence"):
    return _ACTIVE.set(evidence)


def deactivate(token) -> None:
    _ACTIVE.reset(token)


def safely(method, *args, **kwargs) -> None:
    """Fail open: evidence cannot break curation or publication."""
    if method is None:
        return
    try:
        method(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - isolated diagnostics
        log.warning("provenance capture unavailable (%s): %s", type(exc).__name__, exc)


def _candidate_record(story: dict, oid: str, when: dt.datetime) -> dict:
    return {
        "observation_id": oid,
        "article_id": oid.split(".")[0],
        "provider": _clean(story.get("provider"), 32),
        "source_article_id": _safe_source_id(story.get("source_article_id")),
        "source": _clean(story.get("source"), 65),
        "canonical_url": _public_url(story.get("canonical_url") or story.get("link")),
        "headline": _clean(story.get("title"), 170),
        "public_excerpt": _clean(story.get("description"), 100),
        "published_at": _clean(story.get("pub_date"), 40),
        "fetched_at": _clean(story.get("fetched_at"), 40) or when.isoformat(timespec="seconds"),
        "section_hint": _clean(story.get("section_hint"), 24),
        "canada_lane": bool(canada.is_canada_national(story)),
        "major_event_ids": list(canada.matching_major_event_ids(story, when.astimezone(ZoneInfo(config.TIMEZONE)).date()))[:4],
        "stage": "normalized",
    }


class EditionEvidence:
    def __init__(self, *, when: dt.datetime | None = None):
        self.started = when or dt.datetime.now(dt.timezone.utc)
        if self.started.tzinfo is None:
            raise ValueError("evidence timestamp requires timezone")
        self.day = self.started.astimezone(ZoneInfo(config.TIMEZONE)).date().isoformat()
        self.candidates: list[dict] = []
        self._ids: dict[int, str] = {}
        self._ordinal: Counter = Counter()
        self.model_input_ids: list[str] = []
        self.selected: list[dict] = []
        self.unmatched: list[dict] = []
        self.following: list[str] = []
        self.counts: dict = {}
        self.duplicate_groups: list[dict] = []
        self.attempts: list[dict] = []
        self.parse_outcomes: list[str] = []
        self.stages: dict = {}
        self.source_outcomes: list[dict] = []
        self.outcome = "in_progress"
        self.omitted_candidates = 0
        self.build_run_id = _clean(os.environ.get("GITHUB_RUN_ID"), 24) or None
        self.build_attempt = _clean(os.environ.get("GITHUB_RUN_ATTEMPT"), 8) or None
        self.prompt_hash: str | None = None
        self.schema_hash: str | None = None

    def _observe(self, story: dict) -> str:
        existing = self._ids.get(id(story))
        if existing:
            return existing
        article_id = _identity(story)
        self._ordinal[article_id] += 1
        observation_id = f"{article_id}.{self._ordinal[article_id]}"
        self._ids[id(story)] = observation_id
        return observation_id

    def record_source(self, provider: str, lane: str, status: str, count: int = 0) -> None:
        """Record public-safe per-request outcomes; never store errors or URLs."""
        if len(self.source_outcomes) >= 32:
            return
        if status not in {"ok", "empty", "error", "malformed", "missing_key"}:
            return
        self.source_outcomes.append({
            "provider": _clean(provider, 32),
            "lane": _clean(lane, 50),
            "status": status,
            "items_returned": max(0, int(count)),
        })

    def record_pool(self, raw: list, stories: list[dict]) -> None:
        self.counts["raw_fetched"] = len(raw)
        self.counts["normalized"] = len(stories)
        self.counts["raw_by_provider"] = dict(sorted(Counter(
            str(item.get("_src", "unknown")) for item in raw if isinstance(item, dict)
        ).items()))
        self.stages["fetch"] = (
            "complete_with_source_outcomes" if self.source_outcomes
            else "complete_with_source_level_outages_unreported"
        )
        self.counts["source_requests"] = dict(sorted(Counter(
            item["status"] for item in self.source_outcomes
        ).items()))
        self.stages["normalize"] = "complete"
        for story in stories:
            oid = self._observe(story)
            if len(self.candidates) >= MAX_CANDIDATES:
                self.omitted_candidates += 1
                continue
            self.candidates.append(_candidate_record(story, oid, self.started))

    def record_following(self, editorial: list[dict], following: list[dict]) -> None:
        retained = {id(s) for s in editorial}
        self.counts["after_following"] = len(editorial)
        self.following = [_identity(s) for s in following][:config.VOICE_FOLLOWING_CAP]
        self.counts["following_selected"] = len(following)
        self.stages["following"] = "complete"
        self._eligible = retained

    def record_sports(self, editorial: list[dict], count: int) -> None:
        self.counts["sports_duplicates_suppressed"] = count
        self.counts["after_sports"] = len(editorial)
        self.stages["sports"] = "complete"
        self._sports_eligible = {id(s) for s in editorial}

    def record_trim(self, stories: list[dict], selected: list[dict], today: dt.date) -> None:
        self.counts["curation_eligible"] = len(stories)
        groups: dict[str, list[str]] = defaultdict(list)
        for story in stories:
            groups[_identity(story)].append(self._observe(story))
        self.duplicate_groups = [
            {"article_id": article_id, "observations": oids[:12], "total": len(oids)}
            for article_id, oids in groups.items() if len(oids) > 1
        ][:40]
        self.counts["exact_duplicate_suppressed"] = sum(len(v) - 1 for v in groups.values())
        self.model_input_ids = [self._observe(story) for story in selected]
        self.counts["sent_to_model"] = len(selected)
        self.counts["input_canada"] = sum(bool(canada.is_canada_national(s)) for s in selected)
        self.counts["input_major_events"] = sum(bool(canada.matching_major_event_ids(s, today)) for s in selected)
        chosen = set(self.model_input_ids)
        # Large source pools are summarized, but every item actually handed
        # to Gemini must remain independently auditable.
        stored = {c["observation_id"] for c in self.candidates}
        for selected_story in selected:
            oid = self._observe(selected_story)
            if oid in stored:
                continue
            if len(self.candidates) == MAX_CANDIDATES:
                victim = next((i for i in range(len(self.candidates) - 1, -1, -1)
                               if self.candidates[i]["observation_id"] not in chosen), None)
                if victim is None:
                    break
                stored.discard(self.candidates[victim]["observation_id"])
                self.candidates.pop(victim)
                self.omitted_candidates += 1
            self.candidates.append(_candidate_record(selected_story, oid, self.started))
            stored.add(oid)
            self.omitted_candidates = max(0, self.omitted_candidates - 1)
        duplicate_tail = {oid for ids in groups.values() for oid in ids[1:]}
        for candidate in self.candidates:
            oid = candidate["observation_id"]
            if oid in chosen:
                candidate["stage"] = "model_input"
            elif oid in duplicate_tail:
                candidate["stage"] = "exact_duplicate"
            elif id_by_oid := self._object_id(oid):
                if hasattr(self, "_eligible") and id_by_oid not in self._eligible:
                    candidate["stage"] = "following_suppression"
                elif hasattr(self, "_sports_eligible") and id_by_oid not in self._sports_eligible:
                    candidate["stage"] = "sports_suppression"
                else:
                    candidate["stage"] = "not_in_bounded_input"
            else:
                candidate["stage"] = "not_in_bounded_input"
        self.stages["trim"] = "complete"

    def _object_id(self, oid: str) -> int | None:
        return next((objid for objid, key in self._ids.items() if key == oid), None)

    def record_prompt(self, model: str, instruction: str, *, has_following: bool) -> None:
        self.prompt_hash = _digest(instruction)
        self.schema_hash = _digest(
            json.dumps({"curation_sections": config.CURATION_SECTIONS, "following": has_following,
                        "input_keys": ["title", "description", "source", "section_hint", "pub_date", "image", "link"]},
                       sort_keys=True)
        )
        self.stages["model"] = "attempted"

    def record_attempt(self, *, model: str, attempt: int, duration_ms: int,
                       response=None, code=None, outcome: str = "ok") -> None:
        if len(self.attempts) >= MAX_ATTEMPTS:
            return
        result = {
            "requested_model": config.CURATE_MODEL,
            "attempted_model": _clean(model, 80),
            "actual_model": _clean(getattr(response, "model_version", None), 80) or None,
            "thinking_budget": config.CURATE_THINKING_BUDGET if "2.5" in model else None,
            "retry_index": attempt,
            "fallback": model != config.CURATE_MODEL,
            "duration_ms": max(0, int(duration_ms)),
            "outcome": outcome,
            "provider_status": code if isinstance(code, int) else None,
            "usage": _usage(response),
        }
        self.attempts.append(result)

    def record_parse(self, outcome: str) -> None:
        if len(self.parse_outcomes) < MAX_ATTEMPTS:
            self.parse_outcomes.append(outcome)

    def record_final(self, edition: dict) -> None:
        sources = defaultdict(list)
        for candidate in self.candidates:
            sources[candidate["article_id"]].append(candidate)
        input_sources = {
            article_id: [c for c in options if c["observation_id"] in self.model_input_ids]
            for article_id, options in sources.items()
        }
        for section in edition.get("sections", []):
            if section.get("id") == "sports":
                continue
            for story in section.get("stories", []):
                if not isinstance(story, dict):
                    continue
                article_id = _identity(story) if story.get("link") else None
                match = (input_sources.get(article_id) or [None])[0] if article_id else None
                result = {"section": _clean(section.get("id"), 24),
                          "article_id": match["article_id"] if match else None,
                          "observation_id": match["observation_id"] if match else None}
                self.selected.append(result)
                if match:
                    match["stage"] = "final_selected"
                else:
                    self.unmatched.append({"section": result["section"],
                                           "link_hash": _digest(str(story.get("link") or ""))[:20]})
        self.counts["editorial_final"] = len(self.selected)
        self.counts["following_final"] = len(edition.get("following", []))
        self.counts["unmatched_final_links"] = len(self.unmatched)
        self.stages["selection"] = "complete"
        self.stages["render"] = "pending"

    def _document(self, html_path: Path) -> dict:
        self.outcome = "published"
        self.stages["render"] = "complete"
        return {
            "schema_version": SCHEMA_VERSION,
            "edition_date_toronto": self.day,
            "build_started_utc": self.started.astimezone(dt.timezone.utc).isoformat(timespec="seconds"),
            "build_run_id": self.build_run_id,
            "build_attempt": self.build_attempt,
            "publication": {
                "page_path": "docs/index.html",
                "page_sha256": hashlib.sha256(html_path.read_bytes()).hexdigest(),
                "commit": "same_git_commit_as_page",
            },
            "status": self.outcome,
            "stages": self.stages,
            "counts": self.counts,
            "source_outcomes": self.source_outcomes,
            "candidates": self.candidates,
            "candidates_omitted": self.omitted_candidates,
            "duplicate_groups": self.duplicate_groups,
            "model_input_observation_ids": self.model_input_ids,
            "final_editorial_sources": self.selected,
            "final_unmatched": self.unmatched,
            "following_selected_article_ids": self.following,
            "model": {
                "requested": config.CURATE_MODEL,
                "prompt_sha256": self.prompt_hash,
                "schema_sha256": self.schema_hash,
                "sdk": "google-genai",
                "sdk_version": _sdk_version(),
                "attempts": self.attempts,
                "json_parse_outcomes": self.parse_outcomes,
            },
        }

    def write(self, html_path: Path, *, root: Path = ROOT) -> Path | None:
        """Atomic create-once. Existing edition evidence is never overwritten."""
        path = root / self.day[:4] / self.day[5:7] / f"{self.day}.json"
        if path.exists():
            log.info("edition evidence already exists: %s", path)
            return None
        doc = self._document(Path(html_path))
        def encoded() -> bytes:
            return (json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        data = encoded()
        # Always preserve precise model-input IDs and output identities. Remove
        # less consequential metadata first; the omitted count explains gaps.
        while len(data) > MAX_BYTES and doc["candidates"]:
            idx = next((i for i, c in enumerate(doc["candidates"])
                        if c["observation_id"] not in self.model_input_ids), None)
            if idx is None:
                break
            doc["candidates"].pop(idx)
            doc["candidates_omitted"] += 1
            data = encoded()
        if len(data) > MAX_BYTES:
            raise ValueError("edition evidence exceeds hard size limit")
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".evidence-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                # Exclusive, atomic create: two workers racing for the same
                # edition date cannot replace a previously written record.
                os.link(name, path)
            except FileExistsError:
                return None
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        log.info("wrote %s (%d bytes)", path, len(data))
        return path


def _sdk_version() -> str | None:
    try:
        return importlib.metadata.version("google-genai")
    except importlib.metadata.PackageNotFoundError:
        return None


def read_evidence(path: Path) -> dict:
    """Sentinel read contract: explicit missing / invalid / unsupported status."""
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"status": "missing", "evidence": None}
    except (OSError, ValueError):
        return {"status": "invalid", "evidence": None}
    if not isinstance(record, dict):
        return {"status": "invalid", "evidence": None}
    if record.get("schema_version") != SCHEMA_VERSION:
        return {"status": "unsupported_version", "schema_version": record.get("schema_version"), "evidence": None}
    if record.get("status") != "published" or not isinstance(record.get("publication"), dict):
        return {"status": "invalid", "evidence": None}
    return {"status": "available", "evidence": record}
