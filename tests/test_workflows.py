"""The workflow contract between the morning build and the Voice watcher.

Both jobs commit to the same branch, so the way they avoid overwriting each
other is a correctness property, not a formatting preference. It is asserted
here rather than trusted to review, because the failure mode is a silently
lost edition or a silently lost claim.

The rules, and why each one is what it is:

* **Separate concurrency groups.** GitHub cancels a *pending* run when a newer
  one queues on the same group. Sharing one group between an hourly watcher
  and a five-slot morning build would let the watcher cancel a queued edition.
* **Disjoint write paths.** The build writes ``docs/index.html``; the watcher
  writes ``data/voice_watch_state.json``. Nothing writes both.
* **Safe pushes on both sides.** Each fetches and retries rather than assuming
  it owns the branch. That is what makes the disjoint paths actually safe.
* **The watcher is not a second build.** It must not run ``src.build`` or
  touch the curation model.
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"

BUILD = "build.yml"
WATCH = "voice-watch.yml"
NOTIFY = "notify.yml"
CI = "ci.yml"

STATE_PATH = "data/voice_watch_state.json"
EDITION_PATH = "docs/index.html"


def load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def script(workflow: dict) -> str:
    """Every ``run:`` block in a workflow, concatenated."""
    out = []
    for job in workflow.get("jobs", {}).values():
        for step in job.get("steps", []):
            if step.get("run"):
                out.append(step["run"])
    return "\n".join(out)


def test_the_watcher_workflow_exists_and_is_scheduled():
    watch = load(WATCH)

    # PyYAML parses a bare `on:` key as the boolean True.
    triggers = watch.get("on", watch.get(True))
    crons = [entry["cron"] for entry in triggers["schedule"]]
    assert crons, "the watcher must run on a schedule, not only on demand"
    for cron in crons:
        minute = cron.split()[0]
        assert minute not in ("0", "*"), (
            f"'{cron}' fires at the top of the hour, the most throttled slot"
        )


def test_the_watcher_polls_hourly_at_most():
    """Eventually-soon, not realtime. Sub-hourly would cost provider budget
    for latency GitHub's scheduler cannot actually deliver."""
    watch = load(WATCH)
    triggers = watch.get("on", watch.get(True))

    for entry in triggers["schedule"]:
        minute = entry["cron"].split()[0]
        assert "/" not in minute and "," not in minute, entry["cron"]


def test_build_and_watcher_do_not_share_a_concurrency_group():
    """A shared group would let an hourly watcher cancel a queued edition."""
    build_group = load(BUILD)["concurrency"]["group"]
    watch_group = load(WATCH)["concurrency"]["group"]

    assert build_group != watch_group
    assert load(BUILD)["concurrency"]["cancel-in-progress"] is False
    assert load(WATCH)["concurrency"]["cancel-in-progress"] is False


def test_each_workflow_writes_only_its_own_path():
    build_script, watch_script = script(load(BUILD)), script(load(WATCH))

    assert EDITION_PATH in build_script and STATE_PATH not in build_script
    assert EDITION_PATH not in watch_script


def test_both_writers_push_with_fetch_and_retry():
    """Disjoint paths are only safe if neither push assumes it owns the branch."""
    build_script = script(load(BUILD))

    assert "git fetch origin" in build_script
    assert "git rebase" in build_script
    assert "for attempt in" in build_script

    # The watcher's retry loop lives in Python, where it can be tested; the
    # workflow only invokes it.
    from src.voices.state import GitStateStore

    assert hasattr(GitStateStore, "load") and hasattr(GitStateStore, "save")


def test_the_watcher_never_runs_the_edition_build():
    watch_script = script(load(WATCH))

    assert "src.build" not in watch_script
    assert "src.voice_watch" in watch_script


def test_the_watcher_asks_for_no_key_it_does_not_use():
    """A run that cannot spend Gemini or NYT credit cannot leak or waste it."""
    env: dict = {}
    for job in load(WATCH)["jobs"].values():
        for step in job.get("steps", []):
            env.update(step.get("env", {}))

    assert "GEMINI_API_KEY" not in env
    assert "NYT_API_KEY" not in env
    assert "NTFY_TOPIC" in env


def test_the_watcher_can_write_the_repository():
    assert load(WATCH)["permissions"]["contents"] == "write"


def test_watcher_state_commits_do_not_burn_ci():
    triggers = load(CI).get("on", load(CI).get(True))

    assert STATE_PATH in triggers["push"]["paths-ignore"]


def test_the_morning_push_is_unchanged_and_says_nothing_about_articles():
    """The edition notification must not become a second alert for a piece the
    watcher already announced."""
    notify_script = script(load(NOTIFY))

    assert "Today's edition is ready." in notify_script
    assert "voice" not in notify_script.lower()


def test_the_state_path_the_workflows_assume_is_the_configured_one():
    from src import config

    assert config.VOICE_WATCH_STATE_PATH == STATE_PATH
    assert STATE_PATH in (WORKFLOWS.parents[1] / ".github" / "workflows" / CI).read_text(
        encoding="utf-8"
    )
