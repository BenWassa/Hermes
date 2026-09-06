"""Durable seen state for the release-time watcher.

The watcher's one hard requirement is that a publication produces **at most
one** alert, however many times the job runs, retries, or overlaps with
itself. That is a distributed-systems problem, not a lookup problem, so the
state here is designed around two ideas rather than around "is this URL in a
JSON file".

**The state file is a claim log, not a delivery log.** An entry is written
*before* its notification is attempted, so the ordering of the two operations
decides which way a crash can go. Claim-then-notify can lose an alert (the
runner dies between the two) but can never send a second one. Notify-then-
claim would do the opposite. For a quiet newspaper whose morning edition
already carries every followed piece, a lost alert is a minor inconvenience
and a duplicate alert is the failure the reader would actually notice, so the
claim is written first and an entry is never re-alerted once it exists.

**A git push is a compare-and-swap.** The store below commits state to the
repository, and a push is rejected when the ref moved underneath it. That
rejection is the concurrency primitive: two overlapping runs that both
discover the same article cannot both push, and the loser re-reads state,
sees the winner's claim, and drops the article from its own notify list. It is
what makes overlapping runs safe without relying on a workflow-level lock or
on timing.

An entry stores identity keys, the Voices it was attributed to, timestamps and
a delivery status. It never stores a headline, a description, or any part of
an article body.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .timeparse import parse_timestamp, to_iso

log = logging.getLogger("the-daily.voices.state")

UTC = dt.timezone.utc

STATE_VERSION = 1

#: Claimed, notification not yet confirmed. Never re-alerted: a run that dies
#: between the claim and the send leaves this behind, and re-sending it would
#: be exactly the duplicate this design exists to prevent.
STATUS_PENDING = "pending"
#: Delivered to ntfy.
STATUS_NOTIFIED = "notified"
#: Delivery was attempted and failed. Terminal, for the same reason: the
#: request may have reached ntfy before the error surfaced.
STATUS_FAILED = "failed"
#: Seen, deliberately not alerted (over the per-run alert cap). The morning
#: edition still carries it.
STATUS_SUPPRESSED = "suppressed"
#: Seen at a cold start or after a state recovery, adopted without alerting.
STATUS_ADOPTED = "adopted"

STATUSES = frozenset(
    {STATUS_PENDING, STATUS_NOTIFIED, STATUS_FAILED, STATUS_SUPPRESSED, STATUS_ADOPTED}
)


@dataclass
class SeenEntry:
    """One article the watcher has already accounted for.

    ``keys`` is the full set of identity keys the article was recognised by
    (canonical URL, provider article ids, host fingerprint, syndication and
    reprint-group keys). Recording all of them is what makes a later sighting
    through a *different* adapter, or of a syndicated reprint, match the same
    entry instead of looking new.
    """

    key: str
    keys: tuple[str, ...] = ()
    voice_ids: tuple[str, ...] = ()
    first_seen: dt.datetime | None = None
    published_at: dt.datetime | None = None
    status: str = STATUS_PENDING
    attempts: int = 0
    error: str = ""

    def as_dict(self) -> dict:
        out: dict = {
            "keys": sorted(self.keys),
            "voice_ids": list(self.voice_ids),
            "first_seen": to_iso(self.first_seen),
            "published_at": to_iso(self.published_at),
            "status": self.status,
        }
        if self.attempts:
            out["attempts"] = self.attempts
        if self.error:
            out["error"] = self.error[:200]
        return out


@dataclass
class WatchState:
    """The whole durable state of the watcher.

    ``cold`` (no file yet) and ``recovered`` (the file was unusable) both mean
    the same thing operationally: this run has no trustworthy record of what
    the reader has already been told, so it adopts what it finds without
    alerting instead of announcing a back catalogue.
    """

    version: int = STATE_VERSION
    entries: dict[str, SeenEntry] = field(default_factory=dict)
    last_reconcile_at: dt.datetime | None = None
    updated_at: dt.datetime | None = None
    cold: bool = False
    recovered: bool = False
    problems: tuple[str, ...] = ()

    @property
    def untrusted(self) -> bool:
        """True when this run must adopt silently rather than alert."""
        return self.cold or self.recovered

    # -- lookup ------------------------------------------------------------

    def index(self) -> dict[str, str]:
        """Every identity key -> the entry key that owns it."""
        out: dict[str, str] = {}
        for entry in self.entries.values():
            for key in (entry.key, *entry.keys):
                out.setdefault(key, entry.key)
        return out

    def find(self, keys) -> SeenEntry | None:
        """The entry matching any of ``keys``, or None."""
        index = self.index()
        for key in keys:
            owner = index.get(key)
            if owner is not None:
                return self.entries.get(owner)
        return None

    def has(self, keys) -> bool:
        return self.find(keys) is not None

    # -- mutation ----------------------------------------------------------

    def claim(
        self,
        key: str,
        keys,
        *,
        voice_ids,
        first_seen: dt.datetime,
        published_at: dt.datetime | None,
        status: str = STATUS_PENDING,
    ) -> SeenEntry:
        """Record an article as accounted for. Never overwrites an existing entry.

        Returning the existing entry rather than replacing it is deliberate: a
        claim is a one-way door, and re-claiming would reset a delivery status
        and reopen the article for a second alert.
        """
        existing = self.find([key, *keys])
        if existing is not None:
            return existing
        entry = SeenEntry(
            key=key,
            keys=tuple(sorted({key, *keys})),
            voice_ids=tuple(voice_ids),
            first_seen=first_seen,
            published_at=published_at,
            status=status,
        )
        self.entries[key] = entry
        return entry

    def mark(self, key: str, status: str, *, error: str = "", attempted: bool = False) -> None:
        """Record the outcome of a delivery attempt on an existing claim."""
        entry = self.entries.get(key)
        if entry is None:
            return
        entry.status = status
        entry.error = error
        if attempted:
            entry.attempts += 1

    def prune(self, now: dt.datetime, *, retention: dt.timedelta, max_entries: int) -> int:
        """Bound state growth. Returns how many entries were dropped.

        Two independent bounds, because either alone can fail. Retention keeps
        the file from accumulating a year of history; the hard cap keeps it
        bounded even if a source starts emitting a large back catalogue with
        recent timestamps. Retention must stay longer than the watcher's
        lookback window or a still-alertable article could be forgotten and
        alerted a second time.
        """
        cutoff = now - retention
        dropped = [
            key
            for key, entry in self.entries.items()
            if (entry.first_seen or now) < cutoff
        ]
        for key in dropped:
            del self.entries[key]

        if len(self.entries) > max_entries:
            ordered = sorted(
                self.entries.items(),
                key=lambda item: (item[1].first_seen or now, item[0]),
                reverse=True,
            )
            keep = {key for key, _ in ordered[:max_entries]}
            for key in list(self.entries):
                if key not in keep:
                    del self.entries[key]
                    dropped.append(key)

        if dropped:
            log.info("voice watch: pruned %d seen entr(ies)", len(dropped))
        return len(dropped)

    # -- serialisation -----------------------------------------------------

    def as_dict(self) -> dict:
        return {
            "version": STATE_VERSION,
            "updated_at": to_iso(self.updated_at),
            "last_reconcile_at": to_iso(self.last_reconcile_at),
            "seen": {key: self.entries[key].as_dict() for key in sorted(self.entries)},
        }

    def dumps(self) -> str:
        """Deterministic JSON. Identical state always produces an identical file."""
        return json.dumps(self.as_dict(), indent=2, sort_keys=False, ensure_ascii=False) + "\n"

    def fingerprint(self) -> str:
        """Everything that makes this state *different*, ignoring ``updated_at``.

        A run that finds nothing new must leave no commit behind. Stamping the
        run time would defeat that on its own, so the change check compares
        the substance and the timestamp rides along only when something else
        actually moved.
        """
        payload = self.as_dict()
        payload.pop("updated_at", None)
        return json.dumps(payload, sort_keys=True)


# --- parsing --------------------------------------------------------------

def _parse_entry(key: str, raw, problems: list[str]) -> SeenEntry | None:
    if not isinstance(raw, dict):
        problems.append(f"seen['{key}'] is not an object")
        return None
    keys = raw.get("keys")
    if keys is None:
        keys = [key]
    if not isinstance(keys, list) or not all(isinstance(k, str) and k for k in keys):
        problems.append(f"seen['{key}'].keys must be a list of non-empty strings")
        return None
    voice_ids = raw.get("voice_ids") or []
    if not isinstance(voice_ids, list) or not all(isinstance(v, str) for v in voice_ids):
        problems.append(f"seen['{key}'].voice_ids must be a list of strings")
        return None
    first_seen = parse_timestamp(raw.get("first_seen"))
    if first_seen is None:
        problems.append(f"seen['{key}'].first_seen is missing or unparseable")
        return None
    status = raw.get("status", STATUS_PENDING)
    if status not in STATUSES:
        problems.append(f"seen['{key}'].status '{status}' is not a known status")
        return None
    attempts = raw.get("attempts", 0)
    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 0:
        problems.append(f"seen['{key}'].attempts must be a non-negative integer")
        return None
    return SeenEntry(
        key=key,
        keys=tuple(sorted({key, *keys})),
        voice_ids=tuple(voice_ids),
        first_seen=first_seen,
        published_at=parse_timestamp(raw.get("published_at")),
        status=status,
        attempts=attempts,
        error=str(raw.get("error", ""))[:200],
    )


def parse_state(data) -> tuple[WatchState, list[str]]:
    """Parse state data, keeping whatever is usable and reporting the rest.

    Entries that survive are kept even when their neighbours are broken, so a
    recovery never re-alerts articles the file still remembers correctly. The
    caller decides what the problems mean; ``load_state`` treats any problem
    as "this file is not trustworthy this run".
    """
    problems: list[str] = []
    if not isinstance(data, dict):
        return WatchState(), ["state must be a JSON object"]

    version = data.get("version", STATE_VERSION)
    if version != STATE_VERSION:
        problems.append(f"unsupported state version {version!r} (expected {STATE_VERSION})")

    raw_seen = data.get("seen", {})
    entries: dict[str, SeenEntry] = {}
    if not isinstance(raw_seen, dict):
        problems.append("state.seen must be an object keyed by article identity")
        raw_seen = {}
    for key, raw in raw_seen.items():
        if not isinstance(key, str) or not key:
            problems.append("state.seen has a non-string key")
            continue
        entry = _parse_entry(key, raw, problems)
        if entry is not None:
            entries[key] = entry

    return (
        WatchState(
            version=STATE_VERSION,
            entries=entries,
            last_reconcile_at=parse_timestamp(data.get("last_reconcile_at")),
            updated_at=parse_timestamp(data.get("updated_at")),
            problems=tuple(problems),
        ),
        problems,
    )


def state_from_text(text: str) -> WatchState:
    """Parse serialized state, flagging an untrustworthy file rather than raising.

    Shared by ``load_state`` and by test doubles, so a fake store degrades
    exactly the way the real one does.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return WatchState(recovered=True, problems=(f"not valid JSON: {exc}",))
    state, problems = parse_state(data)
    if problems:
        state.recovered = True
    return state


def load_state(path: Path | str) -> WatchState:
    """Read state from disk, degrading safely rather than raising.

    Three outcomes, and each is a decision rather than an accident:

    * **No file.** A cold start. Marked ``cold``; the run adopts what it finds
      without alerting, because announcing a day of back catalogue on first
      install is not what a quiet newspaper does.
    * **Unreadable or invalid.** Marked ``recovered``, with whatever entries
      did parse retained. The run adopts silently and rewrites the file clean,
      so one bad file costs one silent cycle instead of a burst of duplicates.
    * **Valid.** Normal operation.
    """
    path = Path(path)
    if not path.exists():
        log.info("voice watch: no state at %s; cold start, adopting without alerting", path)
        return WatchState(cold=True)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        log.error("voice watch: state %s is unreadable (%s); recovering without alerting", path, exc)
        return WatchState(recovered=True, problems=(str(exc),))

    state = state_from_text(text)
    if state.recovered:
        for problem in state.problems:
            log.error("voice watch: state %s: %s", path, problem)
        log.error(
            "voice watch: %d state problem(s); adopting this run's findings without alerting",
            len(state.problems),
        )
    return state


# --- stores ---------------------------------------------------------------

class StateStore:
    """Where durable state lives.

    ``load`` must return the newest state the store can see, and ``save`` must
    return False (rather than raise) when the write lost a race, so the caller
    can re-read and re-decide. That contract is the whole reason the watcher
    can be tested against overlapping runs without a network or a repository.
    """

    def load(self) -> WatchState:
        raise NotImplementedError

    def save(self, state: WatchState, message: str) -> bool:
        raise NotImplementedError


class FileStateStore(StateStore):
    """A plain local file. Used for local runs, ``--no-push``, and tests."""

    def __init__(self, path: Path | str):
        self.path = Path(path)

    def load(self) -> WatchState:
        return load_state(self.path)

    def save(self, state: WatchState, message: str) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(state.dumps(), encoding="utf-8")
        log.info("voice watch: wrote %s (%s)", self.path, message)
        return True


class GitError(RuntimeError):
    """A git command the store depends on failed."""


class GitStateStore(StateStore):
    """Repository-backed state, synchronised by push.

    ``load`` fetches the branch and resets the working tree to it, so every
    run and every retry decides against what is actually on the remote, not
    against a stale checkout or a local commit that lost a race.

    ``save`` commits only the state file and pushes. A rejected push returns
    False; the caller re-loads (which discards the orphaned local commit) and
    re-decides. The morning build writes a different path, so a rebase-free
    reset is safe here: nothing else in the tree is ever this job's to keep.
    """

    def __init__(
        self,
        path: Path | str,
        *,
        repo: Path | str = ".",
        branch: str = "main",
        remote: str = "origin",
        author_name: str = "github-actions[bot]",
        author_email: str = "github-actions[bot]@users.noreply.github.com",
    ):
        self.repo = Path(repo)
        self.path = Path(path)
        self.branch = branch
        self.remote = remote
        self.author_name = author_name
        self.author_email = author_email

    # -- git plumbing ------------------------------------------------------

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["git", *args],
            cwd=str(self.repo),
            capture_output=True,
            text=True,
            check=False,
        )
        if check and result.returncode != 0:
            raise GitError(
                f"git {' '.join(args)} failed ({result.returncode}): "
                f"{(result.stderr or result.stdout).strip()}"
            )
        return result

    @property
    def _relative(self) -> str:
        try:
            return self.path.resolve().relative_to(self.repo.resolve()).as_posix()
        except ValueError:
            return self.path.as_posix()

    def _assert_clean_enough(self) -> None:
        """Refuse to reset a tree that has work in it other than our own file.

        ``load`` discards local changes, which is right on a CI runner and
        catastrophic on a developer's machine. This is the guard.
        """
        # --untracked-files=all: without it git collapses a new directory to
        # "data/", which would read as unrelated work the first time the state
        # file is created.
        status = self._git("status", "--porcelain", "--untracked-files=all").stdout.splitlines()
        stray = [line for line in status if line[3:].strip().strip('"') != self._relative]
        if stray:
            raise GitError(
                "refusing to synchronise state: the working tree has changes outside "
                f"{self._relative}: {', '.join(s[3:] for s in stray[:5])}. "
                "Use --no-push for a local run."
            )

    # -- StateStore --------------------------------------------------------

    def load(self) -> WatchState:
        self._assert_clean_enough()
        self._git("fetch", self.remote, self.branch)
        self._git("reset", "--hard", f"{self.remote}/{self.branch}")
        # reset leaves an *untracked* state file alone, which would let a
        # half-written file from a killed run be read as the remote's state.
        # Scoped to the one path, so nothing else in the tree is touched.
        self._git("clean", "--force", "--", self._relative, check=False)
        return load_state(self.path)

    def save(self, state: WatchState, message: str) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(state.dumps(), encoding="utf-8")
        self._git("add", "--", self._relative)
        staged = self._git("diff", "--cached", "--quiet", check=False)
        if staged.returncode == 0:
            log.info("voice watch: state unchanged; nothing committed")
            return True
        self._git(
            "-c", f"user.name={self.author_name}",
            "-c", f"user.email={self.author_email}",
            "commit", "-m", message, "--", self._relative,
        )
        pushed = self._git("push", self.remote, f"HEAD:{self.branch}", check=False)
        if pushed.returncode != 0:
            log.warning(
                "voice watch: state push rejected, another run or the morning build moved %s: %s",
                self.branch, (pushed.stderr or pushed.stdout).strip().splitlines()[-1:] or "",
            )
            return False
        log.info("voice watch: pushed state (%s)", message)
        return True
