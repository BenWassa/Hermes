"""Workflow contract during the V1-to-V2 Voices notification migration.

The morning build, legacy release-alert watcher, and V2 roundup all write to
``main`` during the evidence window. They remain independent products with
separate concurrency groups and disjoint paths; git compare-and-swap/rebase
logic prevents one writer from overwriting another.
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
BUILD = "build.yml"
WATCH = "voice-watch.yml"
ROUNDUP = "voice-roundup.yml"
NOTIFY = "notify.yml"
CI = "ci.yml"

WATCH_STATE_PATH = "data/voice_watch_state.json"
ROUNDUP_STATE_PATH = "data/voice_roundup_state.json"
EDITION_PATH = "docs/index.html"
ROUNDUP_PAGE_PATH = "docs/voices/index.html"
DAILY_CRON = "37 15 * * *"
DAILY_BUILD_SCHEDULE = [
    {"cron": "17 5 * * *", "timezone": "America/Toronto"},
    {"cron": "37 5 * * *", "timezone": "America/Toronto"},
    {"cron": "17 6 * * *", "timezone": "America/Toronto"},
    {"cron": "17 7 * * *", "timezone": "America/Toronto"},
]
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


def script(workflow: dict) -> str:
    return "\n".join(script_for(job) for job in workflow.get("jobs", {}).values())


def env_for(job: dict) -> dict:
    env: dict = {}
    for step in job.get("steps", []):
        if isinstance(step, dict):
            env.update(step.get("env", {}))
    return env


def triggers(workflow: dict) -> dict:
    # PyYAML 1.1 interprets bare `on:` as True.
    return workflow.get("on", workflow.get(True))


def test_legacy_release_watcher_remains_scheduled_during_evidence_window():
    watch = load(WATCH)
    crons = [entry["cron"] for entry in triggers(watch)["schedule"]]

    assert crons == ["37 * * * *"]
    assert "src.voice_watch" in script(watch)
    assert "src.voice_roundup" not in script(watch)


def test_legacy_watcher_remains_bounded_and_model_free():
    watch = load(WATCH)
    env: dict = {}
    for job in watch["jobs"].values():
        env.update(env_for(job))

    assert "GEMINI_API_KEY" not in env
    assert "NYT_API_KEY" not in env
    assert "NTFY_TOPIC" in env
    assert "src.build" not in script(watch)


def test_roundup_has_daily_collection_and_bounded_weekly_slots():
    roundup = load(ROUNDUP)
    crons = {entry["cron"] for entry in triggers(roundup)["schedule"]}

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


def test_weekly_roundup_job_alone_receives_ntfy_and_never_gemini():
    weekly = load(ROUNDUP)["jobs"]["weekly"]
    env = env_for(weekly)

    assert "NTFY_TOPIC" in env
    assert "GEMINI_API_KEY" not in env
    assert "NYT_API_KEY" not in env
    assert "src.voice_roundup weekly" in script_for(weekly)
    assert "src.voice_watch" not in script_for(weekly)


def test_all_three_writers_have_independent_non_cancelling_concurrency_groups():
    build = load(BUILD)
    watch = load(WATCH)
    roundup = load(ROUNDUP)
    groups = {
        build["concurrency"]["group"],
        watch["concurrency"]["group"],
        roundup["concurrency"]["group"],
    }

    assert len(groups) == 3
    assert build["concurrency"]["cancel-in-progress"] is False
    assert watch["concurrency"]["cancel-in-progress"] is False
    assert roundup["concurrency"]["cancel-in-progress"] is False


def test_morning_build_does_not_own_voice_operational_paths():
    build_script = script(load(BUILD))

    assert EDITION_PATH in build_script
    assert WATCH_STATE_PATH not in build_script
    assert ROUNDUP_STATE_PATH not in build_script
    assert ROUNDUP_PAGE_PATH not in build_script
    assert "src.voice_watch" not in build_script
    assert "src.voice_roundup" not in build_script


def test_all_repository_writers_use_safe_retry_or_compare_and_swap():
    build_script = script(load(BUILD))

    assert "git fetch origin" in build_script
    assert "git rebase" in build_script
    assert "for attempt in" in build_script

    from src.voices.roundup_state import GitRoundupStore
    from src.voices.state import GitStateStore

    assert hasattr(GitStateStore, "load") and hasattr(GitStateStore, "save")
    assert hasattr(GitRoundupStore, "load")
    assert hasattr(GitRoundupStore, "save_state")
    assert hasattr(GitRoundupStore, "publish")


def test_operational_voice_commits_do_not_burn_ci():
    ignored = set(triggers(load(CI))["push"]["paths-ignore"])

    assert WATCH_STATE_PATH in ignored
    assert ROUNDUP_STATE_PATH in ignored
    assert ROUNDUP_PAGE_PATH in ignored


def test_configured_state_paths_match_workflow_contract():
    from src import config
    from src.voices import roundup_settings as settings

    assert config.VOICE_WATCH_STATE_PATH == WATCH_STATE_PATH
    assert settings.STATE_PATH == ROUNDUP_STATE_PATH
    assert settings.PAGE_PATH == ROUNDUP_PAGE_PATH


def test_morning_build_targets_toronto_five_am_with_bounded_recovery():
    build = load(BUILD)
    build_triggers = triggers(build)

    assert "workflow_dispatch" in build_triggers
    assert build_triggers["schedule"] == DAILY_BUILD_SCHEDULE
    assert all(
        entry["timezone"] == "America/Toronto"
        for entry in build_triggers["schedule"]
    )


def test_morning_build_gates_every_attempt_before_provider_or_gemini_work():
    steps = load(BUILD)["jobs"]["build"]["steps"]
    gate_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Check whether today's edition already exists"
    )
    gate_script = steps[gate_index]["run"]

    assert "TZ=America/Toronto date +%Y-%m-%d" in gate_script
    assert "chore(edition): publish ${TODAY} edition" in gate_script
    assert "github.event_name" not in gate_script

    for step_name in ("Set up Python", "Install dependencies", "Build edition", "Commit and push"):
        index = next(
            index for index, step in enumerate(steps) if step.get("name") == step_name
        )
        assert index > gate_index
        assert steps[index]["if"] == "steps.gate.outputs.skip != 'true'"


def test_morning_notification_has_no_duplicate_manual_bypass():
    notify = load(NOTIFY)
    notify_triggers = triggers(notify)
    notify_script = script(notify)

    assert "workflow_dispatch" not in notify_triggers
    assert notify_triggers["workflow_run"]["workflows"] == ["Build The Daily"]
    assert notify_triggers["workflow_run"]["types"] == ["completed"]
    assert "github.event.workflow_run.conclusion" in notify_script
    assert "COMMIT_EPOCH" in notify_script
    assert "RUN_STARTED_EPOCH" in notify_script
    assert '"$COMMIT_EPOCH" -ge "$RUN_STARTED_EPOCH"' in notify_script


def test_morning_push_remains_one_plain_edition_notification():
    notify_script = script(load(NOTIFY))

    assert "Today's edition is ready." in notify_script
    assert "voice" not in notify_script.lower()
