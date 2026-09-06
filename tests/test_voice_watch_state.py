"""Durable seen state: schema, recovery, bounds, and the git store's guards.

These are the properties the at-most-once argument rests on, tested apart from
the watcher run so a failure here points at the state layer rather than at
orchestration.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess

import pytest

from src import config
from src.voices.state import (
    STATUS_ADOPTED,
    STATUS_FAILED,
    STATUS_NOTIFIED,
    STATUS_PENDING,
    FileStateStore,
    GitError,
    GitStateStore,
    SeenEntry,
    WatchState,
    load_state,
    parse_state,
    state_from_text,
)

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 9, 5, 18, 0, tzinfo=UTC)


def _state(*entries: SeenEntry) -> WatchState:
    return WatchState(entries={entry.key: entry for entry in entries})


def _entry(key: str, *, keys=(), first_seen=NOW, status=STATUS_NOTIFIED) -> SeenEntry:
    return SeenEntry(
        key=key,
        keys=tuple({key, *keys}),
        voice_ids=("jane-doe",),
        first_seen=first_seen,
        published_at=first_seen,
        status=status,
    )


# --- lookup across every key an article carries ---------------------------

def test_an_entry_is_found_by_any_of_its_identity_keys():
    state = _state(_entry("url:https://example.com/a", keys=["pid:perigon:99", "fp:example.com|a|2026-09-05"]))

    assert state.has(["url:https://example.com/a"])
    assert state.has(["pid:perigon:99"])
    assert state.has(["fp:example.com|a|2026-09-05"])
    # A key set that shares nothing is a different article.
    assert not state.has(["url:https://example.com/b"])


def test_claim_never_overwrites_an_existing_entry():
    """A claim is a one-way door. Re-claiming would reopen an alert."""
    state = _state(_entry("url:https://example.com/a", status=STATUS_NOTIFIED))

    returned = state.claim(
        "url:https://example.com/a", ["url:https://example.com/a"],
        voice_ids=["someone-else"], first_seen=NOW, published_at=NOW, status=STATUS_PENDING,
    )

    assert returned.status == STATUS_NOTIFIED
    assert returned.voice_ids == ("jane-doe",)
    assert len(state.entries) == 1


def test_claim_matching_only_a_secondary_key_does_not_create_a_second_entry():
    state = _state(_entry("url:https://example.com/a", keys=["pid:guardian:x/y"]))

    state.claim(
        "url:https://amp.example.com/a", ["pid:guardian:x/y"],
        voice_ids=["jane-doe"], first_seen=NOW, published_at=NOW,
    )

    assert len(state.entries) == 1


# --- serialisation --------------------------------------------------------

def test_state_round_trips_and_is_byte_stable():
    state = _state(
        _entry("url:https://example.com/b"),
        _entry("url:https://example.com/a", status=STATUS_FAILED),
    )
    state.last_reconcile_at = NOW
    state.updated_at = NOW

    first = state.dumps()
    reloaded = state_from_text(first)

    assert not reloaded.recovered
    assert set(reloaded.entries) == set(state.entries)
    assert reloaded.last_reconcile_at == NOW
    reloaded.updated_at = NOW
    assert reloaded.dumps() == first


def test_state_never_stores_article_text():
    """Licensing and privacy: state is identities and timestamps, nothing else."""
    entry = _entry("url:https://example.com/a")
    fields = set(entry.as_dict())

    assert fields <= {"keys", "voice_ids", "first_seen", "published_at", "status", "attempts", "error"}
    assert "title" not in fields and "description" not in fields and "body" not in fields


def test_error_text_is_bounded():
    state = _state(_entry("url:https://example.com/a"))
    state.mark("url:https://example.com/a", STATUS_FAILED, error="x" * 5000, attempted=True)

    assert len(state.entries["url:https://example.com/a"].as_dict()["error"]) == 200


# --- malformed state ------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "{ not json",
        "[]",
        '{"version": 1, "seen": []}',
        '{"version": 9, "seen": {}}',
        '{"version": 1, "seen": {"url:a": "not-an-object"}}',
        '{"version": 1, "seen": {"url:a": {"first_seen": "nonsense"}}}',
        '{"version": 1, "seen": {"url:a": {"first_seen": "2026-09-05T00:00:00Z", "status": "sent"}}}',
        '{"version": 1, "seen": {"url:a": {"first_seen": "2026-09-05T00:00:00Z", "attempts": -1}}}',
        '{"version": 1, "seen": {"url:a": {"first_seen": "2026-09-05T00:00:00Z", "keys": [1, 2]}}}',
    ],
)
def test_malformed_state_is_marked_untrusted_rather_than_read_as_empty(text):
    """Unreadable state must never be mistaken for "nothing has been alerted"."""
    state = state_from_text(text)

    assert state.recovered
    assert state.untrusted


def test_a_partly_broken_file_keeps_the_entries_that_did_parse():
    """Recovery should not throw away the history it can still read."""
    text = json.dumps({
        "version": 1,
        "seen": {
            "url:https://example.com/good": {
                "keys": ["url:https://example.com/good"],
                "voice_ids": ["jane-doe"],
                "first_seen": "2026-09-05T10:00:00Z",
                "status": "notified",
            },
            "url:https://example.com/bad": {"first_seen": "not a date"},
        },
    })

    state = state_from_text(text)

    assert state.recovered
    assert "url:https://example.com/good" in state.entries
    assert "url:https://example.com/bad" not in state.entries


def test_missing_file_is_a_cold_start_not_a_recovery(tmp_path):
    state = load_state(tmp_path / "absent.json")

    assert state.cold and not state.recovered and state.untrusted


def test_unreadable_file_is_a_recovery(tmp_path):
    path = tmp_path / "state"
    path.mkdir()  # a directory: read_text raises OSError, not a JSON error

    state = load_state(path)

    assert state.recovered


def test_valid_state_is_trusted(tmp_path):
    path = tmp_path / "state.json"
    state = _state(_entry("url:https://example.com/a"))
    state.updated_at = NOW
    path.write_text(state.dumps(), encoding="utf-8")

    loaded = load_state(path)

    assert not loaded.untrusted
    assert loaded.has(["url:https://example.com/a"])


def test_parse_state_reports_every_problem_it_found():
    _, problems = parse_state({"version": 4, "seen": {"a": {}}})

    assert len(problems) == 2


# --- bounded growth -------------------------------------------------------

def test_prune_drops_entries_past_the_retention_window():
    old = _entry("url:old", first_seen=NOW - dt.timedelta(days=30))
    recent = _entry("url:recent", first_seen=NOW - dt.timedelta(days=1))
    state = _state(old, recent)

    dropped = state.prune(NOW, retention=dt.timedelta(days=14), max_entries=100)

    assert dropped == 1
    assert set(state.entries) == {"url:recent"}


def test_prune_enforces_a_hard_cap_keeping_the_newest():
    state = _state(*[
        _entry(f"url:{i}", first_seen=NOW - dt.timedelta(minutes=i)) for i in range(10)
    ])

    dropped = state.prune(NOW, retention=dt.timedelta(days=14), max_entries=3)

    assert dropped == 7
    assert set(state.entries) == {"url:0", "url:1", "url:2"}


def test_prune_is_a_no_op_when_state_is_small_and_recent():
    state = _state(_entry("url:a"), _entry("url:b"))

    assert state.prune(NOW, retention=dt.timedelta(days=14), max_entries=100) == 0
    assert len(state.entries) == 2


def test_retention_comfortably_exceeds_the_alerting_window():
    """Otherwise an article could be forgotten while still inside the window
    the watcher alerts on, and be alerted a second time."""
    retention_hours = config.VOICE_WATCH_RETENTION_DAYS * 24

    assert retention_hours > config.VOICE_WATCH_LOOKBACK_HOURS * 4


# --- the file store -------------------------------------------------------

def test_file_store_round_trip(tmp_path):
    store = FileStateStore(tmp_path / "nested" / "state.json")
    state = store.load()
    assert state.cold

    state.claim("url:a", ["url:a"], voice_ids=["v"], first_seen=NOW, published_at=NOW)
    assert store.save(state, "first")

    assert store.load().has(["url:a"])


# --- the git store --------------------------------------------------------

def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


@pytest.fixture
def git_repos(tmp_path):
    """A bare "remote" plus two clones, so a real push race can be staged."""
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(remote)], check=True, capture_output=True)

    seed = tmp_path / "seed"
    subprocess.run(["git", "init", "-b", "main", str(seed)], check=True, capture_output=True)
    (seed / "data").mkdir()
    (seed / "README.md").write_text("seed\n", encoding="utf-8")
    _git(seed, "add", "-A")
    _git(seed, "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-m", "seed")
    _git(seed, "remote", "add", "origin", str(remote))
    _git(seed, "push", "origin", "main")

    def clone(name):
        path = tmp_path / name
        subprocess.run(["git", "clone", str(remote), str(path)], check=True, capture_output=True)
        return path

    return remote, clone("a"), clone("b")


def _store(repo):
    return GitStateStore(repo / "data" / "state.json", repo=repo, branch="main")


def test_git_store_commits_and_pushes_only_the_state_file(git_repos):
    _remote, repo_a, repo_b = git_repos
    store = _store(repo_a)

    state = store.load()
    state.claim("url:a", ["url:a"], voice_ids=["v"], first_seen=NOW, published_at=NOW)
    assert store.save(state, "chore(voices): watcher state, 1 new")

    _git(repo_b, "pull", "--ff-only")
    assert (repo_b / "data" / "state.json").exists()
    log = subprocess.run(
        ["git", "log", "-1", "--name-only", "--format=%s"], cwd=repo_b,
        capture_output=True, text=True, check=True,
    ).stdout
    assert "chore(voices): watcher state, 1 new" in log
    assert log.strip().splitlines()[-1] == "data/state.json"


def test_git_store_does_not_commit_when_state_is_unchanged(git_repos):
    _remote, repo_a, _repo_b = git_repos
    store = _store(repo_a)
    state = store.load()
    state.claim("url:a", ["url:a"], voice_ids=["v"], first_seen=NOW, published_at=NOW)
    store.save(state, "first")
    before = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_a, capture_output=True, text=True).stdout

    assert store.save(store.load(), "second")

    after = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_a, capture_output=True, text=True).stdout
    assert before == after


def test_git_store_reports_a_lost_push_race_instead_of_forcing(git_repos):
    """The rejection is the concurrency primitive; losing it must not clobber."""
    _remote, repo_a, repo_b = git_repos

    store_a, store_b = _store(repo_a), _store(repo_b)
    state_a, state_b = store_a.load(), store_b.load()

    state_a.claim("url:a", ["url:a"], voice_ids=["v"], first_seen=NOW, published_at=NOW)
    state_b.claim("url:b", ["url:b"], voice_ids=["v"], first_seen=NOW, published_at=NOW)

    assert store_a.save(state_a, "a wins")
    assert store_b.save(state_b, "b loses") is False

    # The loser re-reads and sees the winner's claim, not its own orphan commit.
    recovered = store_b.load()
    assert recovered.has(["url:a"])
    assert not recovered.has(["url:b"])


def test_git_store_survives_an_edition_commit_landing_on_the_same_branch(git_repos):
    """The morning build writes docs/index.html; the watcher writes state.
    Different paths, so the watcher's retry always converges."""
    _remote, repo_a, repo_b = git_repos

    # The morning build publishes while the watcher is deciding.
    (repo_b / "docs").mkdir()
    (repo_b / "docs" / "index.html").write_text("<html>edition</html>", encoding="utf-8")
    _git(repo_b, "add", "-A")
    _git(repo_b, "-c", "user.name=b", "-c", "user.email=b@e", "commit", "-m", "chore(edition): publish")
    _git(repo_b, "push", "origin", "main")

    store = _store(repo_a)
    state = store.load()  # a stale checkout; load() re-fetches
    state.claim("url:a", ["url:a"], voice_ids=["v"], first_seen=NOW, published_at=NOW)

    assert store.save(state, "watcher state")

    _git(repo_b, "pull", "--ff-only")
    assert (repo_b / "docs" / "index.html").read_text(encoding="utf-8") == "<html>edition</html>"
    assert (repo_b / "data" / "state.json").exists()


def test_git_store_refuses_to_discard_unrelated_local_work(git_repos):
    """load() resets the tree. That is right on a runner and wrong on a laptop."""
    _remote, repo_a, _repo_b = git_repos
    (repo_a / "README.md").write_text("local edit\n", encoding="utf-8")

    with pytest.raises(GitError, match="refusing to synchronise"):
        _store(repo_a).load()


def test_git_store_load_discards_its_own_orphaned_state_edit(git_repos):
    _remote, repo_a, _repo_b = git_repos
    store = _store(repo_a)
    store.path.parent.mkdir(exist_ok=True)
    store.path.write_text("{ garbage", encoding="utf-8")

    state = store.load()

    assert state.cold and not state.recovered


def test_adopted_status_is_a_recognised_state_value():
    text = json.dumps({
        "version": 1,
        "seen": {"url:a": {"first_seen": "2026-09-05T10:00:00Z", "status": STATUS_ADOPTED}},
    })

    assert not state_from_text(text).recovered
