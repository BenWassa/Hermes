"""Workflow contract for the V2 weekly Core Voices roundup."""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
BUILD = "build.yml"
ROUNDUP = "voice-watch.yml"
NOTIFY = "notify.yml"
CI = "ci.yml"

STATE_PATH = "data/voice_roundup_state.json"
PAGE_PATH = "docs/voices/index.html"
DAILY_CRON = "37 15 * * *"
WEEKLY_CRONS = {
    "43 22 * * 0",
    "43 23 * * 0",
    "43 0 * * 1",
    "43 22 * * 1",
}


def load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def script_for(job: dict) -> str:
    return "\n".join(
        step["run"]
        for step in job.get("steps", [])
        if isinstance(step, dict) and step.get("run")
    )


def env_for(job: dict) -> dict:
    env: dict = {}
    for step in job.get("steps", []):
        if isinstance(step, dict):
            env.update(step.get("env", {}))
    return env


def triggers(workflow: dict) -> dict:
    # PyYAML 1.1 interprets bare `on:` as True.
    return workflow.get("on", workflow.get(True))


def test_roundup_replaces_hourly_release_watcher_with_daily_and_weekly_slots():
    workflow = load(ROUNDUP)
    crons = {entry["cron"] for entry in triggers(workflow)["schedule"]}

    assert crons == {DAILY_CRON, *WEEKLY_CRONS}
    assert "37 * * * *" not in crons
    assert all(cron.split()[0] not in {"0", "*"} for cron in crons)


def test_daily_collection_has_no_notification_or_gemini_secret():
    collect = load(ROUNDUP)["jobs"]["collect"]
    env = env_for(collect)

    assert "NTFY_TOPIC" not in env
    assert "GEMINI_API_KEY" not in env
    assert "NYT_API_KEY" not in env
    assert "src.voice_roundup collect" in script_for(collect)
    assert "src.build" not in script_for(collect)


def test_weekly_job_alone_receives_ntfy_and_never_gemini():
    weekly = load(ROUNDUP)["jobs"]["weekly"]
    env = env_for(weekly)

    assert "NTFY_TOPIC" in env
    assert "GEMINI_API_KEY" not in env
    assert "NYT_API_KEY" not in env
    assert "src.voice_roundup weekly" in script_for(weekly)
    assert "src.voice_watch" not in script_for(weekly)


def test_roundup_and_morning_build_remain_independent():
    build = load(BUILD)
    roundup = load(ROUNDUP)

    assert build["concurrency"]["group"] != roundup["concurrency"]["group"]
    assert build["concurrency"]["cancel-in-progress"] is False
    assert roundup["concurrency"]["cancel-in-progress"] is False

    build_script = "\n".join(script_for(job) for job in build["jobs"].values())
    assert STATE_PATH not in build_script
    assert PAGE_PATH not in build_script
    assert "src.voice_roundup" not in build_script


def test_roundup_writer_uses_git_compare_and_swap_for_state_and_page():
    from src.voices.roundup_state import GitRoundupStore

    assert hasattr(GitRoundupStore, "load")
    assert hasattr(GitRoundupStore, "save_state")
    assert hasattr(GitRoundupStore, "publish")


def test_roundup_operational_commits_do_not_burn_ci():
    ignored = set(triggers(load(CI))["push"]["paths-ignore"])

    assert STATE_PATH in ignored
    assert PAGE_PATH in ignored


def test_configured_paths_match_workflow_contract():
    from src.voices import roundup_settings as settings

    assert settings.STATE_PATH == STATE_PATH
    assert settings.PAGE_PATH == PAGE_PATH


def test_morning_push_remains_one_plain_edition_notification():
    notify_script = "\n".join(script_for(job) for job in load(NOTIFY)["jobs"].values())

    assert "Today's edition is ready." in notify_script
    assert "voice" not in notify_script.lower()
