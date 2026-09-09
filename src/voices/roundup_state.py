"""Bounded durable state for the Voices V2 weekly roundup.

This is intentionally separate from ``voice_watch_state.json``. The V1 file is
a release-alert claim log; this file is a small observation accumulator plus
one weekly period claim. Nothing here imports or interprets V1 alert history.

Daily observations are idempotent upserts. The one-way at-most-once boundary is
``last_roundup``: once a period is durably claimed, no later run may notify for
that period, even when the delivery outcome remains ``pending``.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .timeparse import parse_timestamp, to_iso
from .urls import canonical_url

log = logging.getLogger("the-daily.voices.roundup-state")
UTC = dt.timezone.utc

STATE_VERSION = 1
STATUS_PENDING = "pending"
STATUS_NOTIFIED = "notified"
STATUS_FAILED = "failed"
STATUS_EMPTY = "empty"
STATUS_SUPPRESSED = "suppressed"
ROUNDUP_STATUSES = frozenset(
    {STATUS_PENDING, STATUS_NOTIFIED, STATUS_FAILED, STATUS_EMPTY, STATUS_SUPPRESSED}
)

MAX_TITLE = 300
MAX_PUBLICATION = 120
MAX_URL = 1000
MAX_KEY = 1500
MAX_KEYS_PER_ITEM = 32
MAX_VOICES_PER_ITEM = 8


def _clip(value: object, limit: int) -> str:
    text = str(value or "").strip()
    return text[:limit]


def _key_rank(key: str) -> tuple[int, str]:
    prefixes = ("url:", "pid:", "reprint:", "syn:", "fp:")
    for rank, prefix in enumerate(prefixes):
        if key.startswith(prefix):
            return rank, key
    return len(prefixes), key


def _bounded_keys(keys) -> tuple[str, ...]:
    clean = {
        _clip(key, MAX_KEY)
        for key in keys
        if isinstance(key, str) and key.strip()
    }
    return tuple(sorted(clean, key=_key_rank)[:MAX_KEYS_PER_ITEM])


def _prefer_label(a: str, b: str, limit: int) -> str:
    """Order-independent deterministic preference for public metadata."""
    candidates = {_clip(a, limit), _clip(b, limit)} - {""}
    if not candidates:
        return ""
    return min(candidates, key=lambda value: (-len(value), value.casefold(), value))


def _prefer_url(a: str, b: str) -> str:
    """Choose a stable reader destination independent of observation order."""
    candidates = {_clip(a, MAX_URL), _clip(b, MAX_URL)} - {""}
    valid = [value for value in candidates if canonical_url(value)]
    if not valid:
        return ""
    return min(valid, key=lambda value: (len(canonical_url(value)), canonical_url(value), value))


@dataclass
class RoundupItem:
    key: str
    keys: tuple[str, ...] = ()
    voice_ids: tuple[str, ...] = ()
    first_seen: dt.datetime | None = None
    published_at: dt.datetime | None = None
    title: str = ""
    url: str = ""
    publication: str = ""
    first_morning_surfaced_at: dt.datetime | None = None

    def as_dict(self) -> dict:
        return {
            "keys": list(_bounded_keys((self.key, *self.keys))),
            "voice_ids": list(dict.fromkeys(self.voice_ids))[:MAX_VOICES_PER_ITEM],
            "first_seen": to_iso(self.first_seen),
            "published_at": to_iso(self.published_at),
            "title": _clip(self.title, MAX_TITLE),
            "url": _clip(self.url, MAX_URL),
            "publication": _clip(self.publication, MAX_PUBLICATION),
            "first_morning_surfaced_at": to_iso(self.first_morning_surfaced_at),
        }


@dataclass
class RoundupClaim:
    period_id: str
    cutoff: dt.datetime
    claimed_at: dt.datetime
    status: str = STATUS_PENDING
    selection_keys: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "period_id": self.period_id,
            "cutoff": to_iso(self.cutoff),
            "claimed_at": to_iso(self.claimed_at),
            "status": self.status,
            "selection_keys": list(self.selection_keys[:6]),
        }


@dataclass
class RoundupState:
    version: int = STATE_VERSION
    collecting_since: dt.datetime | None = None
    updated_at: dt.datetime | None = None
    last_reconcile_at: dt.datetime | None = None
    last_roundup: RoundupClaim | None = None
    items: dict[str, RoundupItem] = field(default_factory=dict)
    cold: bool = False
    recovered: bool = False
    problems: tuple[str, ...] = ()

    @property
    def untrusted(self) -> bool:
        return self.cold or self.recovered or self.collecting_since is None

    def index(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for item in self.items.values():
            for key in (item.key, *item.keys):
                if key:
                    out.setdefault(key, item.key)
        return out

    def find(self, keys) -> RoundupItem | None:
        index = self.index()
        for key in keys:
            owner = index.get(key)
            if owner is not None:
                return self.items.get(owner)
        return None

    def observe(
        self,
        *,
        key: str,
        keys,
        voice_ids,
        first_seen: dt.datetime,
        published_at: dt.datetime | None,
        title: str,
        url: str,
        publication: str,
        first_morning_surfaced_at: dt.datetime | None = None,
    ) -> tuple[RoundupItem, bool]:
        """Idempotently merge one trusted Core observation into state."""
        all_keys = _bounded_keys((key, *keys))
        existing = self.find(all_keys)
        voices = tuple(sorted({str(v) for v in voice_ids if v}))[:MAX_VOICES_PER_ITEM]

        if existing is None:
            canonical_key = _clip(key, MAX_KEY)
            if not canonical_key:
                canonical_key = all_keys[0] if all_keys else ""
            item = RoundupItem(
                key=canonical_key,
                keys=_bounded_keys((canonical_key, *all_keys)),
                voice_ids=voices,
                first_seen=first_seen,
                published_at=published_at,
                title=_clip(title, MAX_TITLE),
                url=_prefer_url("", url),
                publication=_clip(publication, MAX_PUBLICATION),
                first_morning_surfaced_at=first_morning_surfaced_at,
            )
            self.items[item.key] = item
            return item, True

        before = json.dumps(existing.as_dict(), sort_keys=True)
        existing.keys = _bounded_keys((existing.key, *existing.keys, *all_keys))
        existing.voice_ids = tuple(sorted(set(existing.voice_ids) | set(voices)))[:MAX_VOICES_PER_ITEM]
        existing.first_seen = min(
            value for value in (existing.first_seen, first_seen) if value is not None
        )
        if published_at is not None:
            if existing.published_at is None or published_at < existing.published_at:
                existing.published_at = published_at
        existing.title = _prefer_label(existing.title, title, MAX_TITLE)
        existing.url = _prefer_url(existing.url, url)
        existing.publication = _prefer_label(
            existing.publication, publication, MAX_PUBLICATION
        )
        if first_morning_surfaced_at is not None:
            if (
                existing.first_morning_surfaced_at is None
                or first_morning_surfaced_at < existing.first_morning_surfaced_at
            ):
                existing.first_morning_surfaced_at = first_morning_surfaced_at
        after = json.dumps(existing.as_dict(), sort_keys=True)
        return existing, before != after

    def mark_morning_urls(self, urls, when: dt.datetime) -> int:
        """Mark items actually present in the committed morning artifact."""
        url_keys = {
            f"url:{canonical_url(url)}"
            for url in urls
            if canonical_url(url)
        }
        if not url_keys:
            return 0
        changed = 0
        for item in self.items.values():
            keys = {item.key, *item.keys}
            item_url = canonical_url(item.url)
            if item_url:
                keys.add(f"url:{item_url}")
            if keys.isdisjoint(url_keys):
                continue
            if item.first_morning_surfaced_at is None:
                item.first_morning_surfaced_at = when
                changed += 1
        return changed

    def prune(
        self,
        now: dt.datetime,
        *,
        retention: dt.timedelta,
        max_entries: int,
    ) -> int:
        cutoff = now - retention
        dropped: list[str] = []
        for key, item in list(self.items.items()):
            if (item.first_seen or now) < cutoff:
                dropped.append(key)
                del self.items[key]

        if len(self.items) > max_entries:
            ordered = sorted(
                self.items.items(),
                key=lambda pair: (pair[1].first_seen or now, pair[0]),
                reverse=True,
            )
            keep = {key for key, _ in ordered[:max_entries]}
            for key in list(self.items):
                if key not in keep:
                    dropped.append(key)
                    del self.items[key]
        if dropped:
            log.info("voice roundup: pruned %d item(s)", len(dropped))
        return len(dropped)

    def claim_period(
        self,
        period_id: str,
        *,
        cutoff: dt.datetime,
        claimed_at: dt.datetime,
        selection_keys,
        status: str,
    ) -> RoundupClaim:
        """Claim one weekly period. Existing claim for that period is immutable."""
        if self.last_roundup and self.last_roundup.period_id == period_id:
            return self.last_roundup
        if status not in ROUNDUP_STATUSES:
            raise ValueError(f"unknown roundup status {status!r}")
        claim = RoundupClaim(
            period_id=period_id,
            cutoff=cutoff,
            claimed_at=claimed_at,
            status=status,
            selection_keys=tuple(selection_keys)[:6],
        )
        self.last_roundup = claim
        return claim

    def mark_roundup(self, period_id: str, status: str) -> None:
        if status not in ROUNDUP_STATUSES:
            raise ValueError(f"unknown roundup status {status!r}")
        if self.last_roundup and self.last_roundup.period_id == period_id:
            self.last_roundup.status = status

    def as_dict(self) -> dict:
        return {
            "version": STATE_VERSION,
            "collecting_since": to_iso(self.collecting_since),
            "updated_at": to_iso(self.updated_at),
            "last_reconcile_at": to_iso(self.last_reconcile_at),
            "last_roundup": self.last_roundup.as_dict() if self.last_roundup else None,
            "items": {
                key: self.items[key].as_dict()
                for key in sorted(self.items)
            },
        }

    def dumps(self) -> str:
        return json.dumps(self.as_dict(), indent=2, ensure_ascii=False) + "\n"

    def fingerprint(self) -> str:
        payload = self.as_dict()
        payload.pop("updated_at", None)
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _parse_item(key: str, raw, problems: list[str]) -> RoundupItem | None:
    label = f"items[{key!r}]"
    if not isinstance(raw, dict):
        problems.append(f"{label} must be an object")
        return None
    first_seen = parse_timestamp(raw.get("first_seen"))
    if first_seen is None:
        problems.append(f"{label}.first_seen is missing or invalid")
        return None
    raw_keys = raw.get("keys", [key])
    if not isinstance(raw_keys, list) or not all(
        isinstance(value, str) and value for value in raw_keys
    ):
        problems.append(f"{label}.keys must be non-empty strings")
        return None
    raw_voices = raw.get("voice_ids", [])
    if not isinstance(raw_voices, list) or not all(
        isinstance(value, str) and value for value in raw_voices
    ):
        problems.append(f"{label}.voice_ids must be non-empty strings")
        return None

    title = raw.get("title", "")
    url = raw.get("url", "")
    publication = raw.get("publication", "")
    if not isinstance(title, str) or len(title) > MAX_TITLE:
        problems.append(f"{label}.title is invalid or over {MAX_TITLE} characters")
    if not isinstance(publication, str) or len(publication) > MAX_PUBLICATION:
        problems.append(
            f"{label}.publication is invalid or over {MAX_PUBLICATION} characters"
        )
    if not isinstance(url, str) or len(url) > MAX_URL or (url and not canonical_url(url)):
        problems.append(f"{label}.url is invalid or over {MAX_URL} characters")
    if not isinstance(title, str) or not isinstance(publication, str) or not isinstance(url, str):
        return None

    return RoundupItem(
        key=_clip(key, MAX_KEY),
        keys=_bounded_keys((key, *raw_keys)),
        voice_ids=tuple(sorted(set(raw_voices)))[:MAX_VOICES_PER_ITEM],
        first_seen=first_seen,
        published_at=parse_timestamp(raw.get("published_at")),
        title=_clip(title, MAX_TITLE),
        url=_clip(url, MAX_URL),
        publication=_clip(publication, MAX_PUBLICATION),
        first_morning_surfaced_at=parse_timestamp(raw.get("first_morning_surfaced_at")),
    )


def _parse_claim(raw, problems: list[str]) -> RoundupClaim | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        problems.append("last_roundup must be an object or null")
        return None
    period_id = raw.get("period_id")
    cutoff = parse_timestamp(raw.get("cutoff"))
    claimed_at = parse_timestamp(raw.get("claimed_at"))
    status = raw.get("status")
    keys = raw.get("selection_keys", [])
    if not isinstance(period_id, str) or not period_id:
        problems.append("last_roundup.period_id is missing")
        return None
    if cutoff is None or claimed_at is None:
        problems.append("last_roundup timestamps are invalid")
        return None
    if status not in ROUNDUP_STATUSES:
        problems.append(f"last_roundup.status {status!r} is invalid")
        return None
    if (
        not isinstance(keys, list)
        or len(keys) > 6
        or not all(isinstance(key, str) and key for key in keys)
    ):
        problems.append("last_roundup.selection_keys must contain at most six strings")
        return None
    return RoundupClaim(
        period_id=period_id,
        cutoff=cutoff,
        claimed_at=claimed_at,
        status=status,
        selection_keys=tuple(keys),
    )


def parse_state(data) -> tuple[RoundupState, list[str]]:
    problems: list[str] = []
    if not isinstance(data, dict):
        return RoundupState(), ["state must be a JSON object"]
    version = data.get("version", STATE_VERSION)
    if version != STATE_VERSION:
        problems.append(
            f"unsupported roundup state version {version!r} (expected {STATE_VERSION})"
        )

    collecting_since = parse_timestamp(data.get("collecting_since"))
    if collecting_since is None:
        problems.append("collecting_since is missing or invalid")

    raw_items = data.get("items", {})
    if not isinstance(raw_items, dict):
        problems.append("state.items must be an object")
        raw_items = {}
    items: dict[str, RoundupItem] = {}
    for key, raw in raw_items.items():
        if not isinstance(key, str) or not key or len(key) > MAX_KEY:
            problems.append("state.items has an invalid key")
            continue
        item = _parse_item(key, raw, problems)
        if item is not None:
            items[item.key] = item

    return (
        RoundupState(
            collecting_since=collecting_since,
            updated_at=parse_timestamp(data.get("updated_at")),
            last_reconcile_at=parse_timestamp(data.get("last_reconcile_at")),
            last_roundup=_parse_claim(data.get("last_roundup"), problems),
            items=items,
            problems=tuple(problems),
        ),
        problems,
    )


def state_from_text(text: str) -> RoundupState:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return RoundupState(recovered=True, problems=(f"not valid JSON: {exc}",))
    state, problems = parse_state(data)
    if problems:
        state.recovered = True
    return state


def load_state(path: Path | str) -> RoundupState:
    path = Path(path)
    if not path.exists():
        log.info("voice roundup: no V2 state at %s; establishing a silent baseline", path)
        return RoundupState(cold=True)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return RoundupState(recovered=True, problems=(str(exc),))
    state = state_from_text(text)
    for problem in state.problems:
        log.error("voice roundup: state %s: %s", path, problem)
    return state


class RoundupStore:
    def load(self) -> RoundupState:
        raise NotImplementedError

    def save_state(self, state: RoundupState, message: str) -> bool:
        raise NotImplementedError

    def publish(
        self,
        state: RoundupState,
        page_html: str,
        page_path: Path | str,
        message: str,
    ) -> bool:
        raise NotImplementedError


class FileRoundupStore(RoundupStore):
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def load(self) -> RoundupState:
        return load_state(self.path)

    def save_state(self, state: RoundupState, message: str) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(state.dumps(), encoding="utf-8")
        return True

    def publish(
        self,
        state: RoundupState,
        page_html: str,
        page_path: Path | str,
        message: str,
    ) -> bool:
        page = Path(page_path)
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(page_html, encoding="utf-8")
        return self.save_state(state, message)


class GitRoundupError(RuntimeError):
    pass


class GitRoundupStore(RoundupStore):
    """Git compare-and-swap store for state and the current page.

    Daily collection commits only the state file. Weekly publication commits
    the state claim and ``docs/voices/index.html`` together, so a notification
    can only be sent after both are visible on the branch.
    """

    def __init__(
        self,
        path: Path | str,
        *,
        page_path: Path | str,
        repo: Path | str = ".",
        branch: str = "main",
        remote: str = "origin",
        author_name: str = "github-actions[bot]",
        author_email: str = "github-actions[bot]@users.noreply.github.com",
    ):
        self.repo = Path(repo)
        self.path = Path(path)
        self.page_path = Path(page_path)
        self.branch = branch
        self.remote = remote
        self.author_name = author_name
        self.author_email = author_email

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["git", *args],
            cwd=str(self.repo),
            capture_output=True,
            text=True,
            check=False,
        )
        if check and result.returncode != 0:
            raise GitRoundupError(
                f"git {' '.join(args)} failed ({result.returncode}): "
                f"{(result.stderr or result.stdout).strip()}"
            )
        return result

    def _relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.repo.resolve()).as_posix()
        except ValueError:
            return path.as_posix()

    @property
    def _state_rel(self) -> str:
        return self._relative(self.path)

    @property
    def _page_rel(self) -> str:
        return self._relative(self.page_path)

    def _assert_clean_enough(self) -> None:
        allowed = {self._state_rel, self._page_rel}
        lines = self._git(
            "status", "--porcelain", "--untracked-files=all"
        ).stdout.splitlines()
        stray = [
            line for line in lines
            if line[3:].strip().strip('"') not in allowed
        ]
        if stray:
            raise GitRoundupError(
                "refusing to synchronise roundup state: working tree has unrelated "
                f"changes: {', '.join(line[3:] for line in stray[:5])}"
            )

    def load(self) -> RoundupState:
        self._assert_clean_enough()
        self._git("fetch", self.remote, self.branch)
        self._git("reset", "--hard", f"{self.remote}/{self.branch}")
        self._git("clean", "--force", "--", self._state_rel, self._page_rel, check=False)
        return load_state(self.path)

    def _commit_and_push(self, paths: list[str], message: str) -> bool:
        self._git("add", "--", *paths)
        staged = self._git("diff", "--cached", "--quiet", check=False)
        if staged.returncode == 0:
            return True
        self._git(
            "-c", f"user.name={self.author_name}",
            "-c", f"user.email={self.author_email}",
            "commit", "-m", message, "--", *paths,
        )
        pushed = self._git(
            "push", self.remote, f"HEAD:{self.branch}", check=False
        )
        if pushed.returncode != 0:
            log.warning(
                "voice roundup: push race lost on %s: %s",
                self.branch,
                (pushed.stderr or pushed.stdout).strip().splitlines()[-1:] or "",
            )
            return False
        return True

    def save_state(self, state: RoundupState, message: str) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(state.dumps(), encoding="utf-8")
        return self._commit_and_push([self._state_rel], message)

    def publish(
        self,
        state: RoundupState,
        page_html: str,
        page_path: Path | str,
        message: str,
    ) -> bool:
        page = Path(page_path)
        if self._relative(page) != self._page_rel:
            raise GitRoundupError("roundup page path does not match store configuration")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        page.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(state.dumps(), encoding="utf-8")
        page.write_text(page_html, encoding="utf-8")
        return self._commit_and_push(
            [self._state_rel, self._page_rel], message
        )
