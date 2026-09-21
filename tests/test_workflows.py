"""Workflow contract for the independent Daily and Voices products.

The morning build, silent Core collection, manual Voice inspection, and screened
weekly digest remain separate. Only the weekly Voice job receives ntfy/Gemini
capability; release-time article notifications are retired.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

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
RECENT_PAGE_PATH = "docs/voices/recent/**"
DAILY_CRON = "37 15 * * *"
DAILY_BUILD_SCHEDULE = [{"cron": "17,47 5-12 * * *"}]
DAILY_PUSH_IGNORES = {
    EDITION_PATH,
    WATCH_STATE_PATH,
    ROUNDUP_STATE_PATH,
    "docs/voices/**",
    "docs/open/**",
    "docs/closed/**",
    "docs/ISSUE_TRACKING.md",
}
WEEKLY_CRONS = {
    "43 22 * * 0",
    "43 23 * * 0",
    "43 0 * * 1",
    "43 22 * * 1",
}
TORONTO = ZoneInfo("America/Toronto")


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


def named_step(workflow: dict, name: str) -> dict:
    return next(
        step
        for step in workflow["jobs"]["build"]["steps"]
        if step.get("name") == name
    )


def expected_daily_gate_outcome(
    *, event: str, local_hour: int, edition_exists: bool
) -> str:
    """Executable statement of the locked #64/#68 gate policy."""
    if edition_exists:
        return "already-published-noop"
    if event == "schedule" and local_hour < 5:
        return "pre-05-scheduled-noop"
    if event == "push" and not 5 <= local_hour <= 11:
        return "push-window-noop"
    return "build-required"


def test_release_watcher_is_manual_read_only_inspection_only():
    watch = load(WATCH)
    watch_triggers = triggers(watch)
    env: dict = {}
    for job in watch["jobs"].values():
        env.update(env_for(job))

    assert set(watch_triggers) == {"workflow_dispatch"}
    assert "schedule" not in watch_triggers
    assert watch["permissions"]["contents"] == "read"
    assert "src.voice_watch --dry-run" in script(watch)
    assert "GEMINI_API_KEY" not in env
    assert "NTFY_TOPIC" not in env
    assert "src.voice_digest" not in script(watch)


def test_roundup_has_daily_collection_and_bounded_weekly_slots():
    roundup = load(ROUNDUP)
    crons = {entry["cron"] for entry in triggers(roundup)["schedule"]}

    assert crons == {DAILY_CRON, *WEEKLY_CRONS}
    assert "37 * * * *" not in crons
    assert all(cron.split()[0] not in {"0", "*"} for cron in crons)


def test_daily_collection_is_silent_and_refreshes_quiet_recent_shelf():
    collect = load(ROUNDUP)["jobs"]["collect"]
    env = env_for(collect)
    text = script_for(collect)

    assert "NTFY_TOPIC" not in env
    assert "GEMINI_API_KEY" not in env
    assert "NYT_API_KEY" not in env
    assert "src.voice_roundup collect" in text
    assert "src.voice_digest recent" in text
    assert "src.voice_weekly weekly" not in text
    assert "src.build" not in text


def test_weekly_digest_job_is_the_only_voice_job_with_ntfy_and_gemini():
    roundup = load(ROUNDUP)
    weekly = roundup["jobs"]["weekly"]
    env = env_for(weekly)

    assert "NTFY_TOPIC" in env
    assert "GEMINI_API_KEY" in env
    assert "NYT_API_KEY" not in env
    assert "src.voice_weekly weekly" in script_for(weekly)
    assert "src.voice_digest weekly" not in script_for(weekly)
    assert "src.voice_watch" not in script_for(weekly)

    watch_env: dict = {}
    for job in load(WATCH)["jobs"].values():
        watch_env.update(env_for(job))
    collect_env = env_for(roundup["jobs"]["collect"])
    assert "NTFY_TOPIC" not in watch_env
    assert "NTFY_TOPIC" not in collect_env
    assert "GEMINI_API_KEY" not in watch_env
    assert "GEMINI_API_KEY" not in collect_env


def test_daily_weekly_and_manual_inspection_have_independent_non_cancelling_groups():
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
    assert "src.voice_digest" not in build_script
    assert "src.voice_weekly" not in build_script


def test_repository_writers_keep_safe_retry_or_compare_and_swap():
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
    assert RECENT_PAGE_PATH in ignored
    assert "docs/voices/articles/**" in ignored


def test_configured_state_paths_match_workflow_contract():
    from src import config
    from src.voices import roundup_settings as settings

    assert config.VOICE_WATCH_STATE_PATH == WATCH_STATE_PATH
    assert settings.STATE_PATH == ROUNDUP_STATE_PATH
    assert settings.PAGE_PATH == ROUNDUP_PAGE_PATH


def test_morning_build_uses_bounded_utc_cadence_with_toronto_schedule_floor():
    build = load(BUILD)
    build_triggers = triggers(build)

    assert "workflow_dispatch" in build_triggers
    assert build_triggers["schedule"] == DAILY_BUILD_SCHEDULE
    assert all("timezone" not in entry for entry in build_triggers["schedule"])

    gate_script = named_step(build, "Check whether today's edition already exists")["run"]
    assert "TZ=America/Toronto date +%H" in gate_script
    assert '"$EVENT" = "schedule"' in gate_script
    assert '"$LOCAL_HOUR" -lt 5' in gate_script
    assert '"$LOCAL_HOUR" -gt 7' not in gate_script
    assert "pre-05-scheduled-noop" in gate_script


@pytest.mark.parametrize(
    ("event", "local_hour", "edition_exists", "expected"),
    [
        ("schedule", 4, False, "pre-05-scheduled-noop"),
        ("schedule", 5, False, "build-required"),
        ("schedule", 7, False, "build-required"),
        ("schedule", 10, False, "build-required"),
        ("schedule", 14, False, "build-required"),
        ("schedule", 23, False, "build-required"),
        ("schedule", 10, True, "already-published-noop"),
        ("push", 4, False, "push-window-noop"),
        ("push", 5, False, "build-required"),
        ("push", 11, False, "build-required"),
        ("push", 12, False, "push-window-noop"),
        ("workflow_dispatch", 2, False, "build-required"),
        ("workflow_dispatch", 22, False, "build-required"),
        ("workflow_dispatch", 22, True, "already-published-noop"),
    ],
)
def test_daily_gate_policy_matrix(event, local_hour, edition_exists, expected):
    assert (
        expected_daily_gate_outcome(
            event=event,
            local_hour=local_hour,
            edition_exists=edition_exists,
        )
        == expected
    )


def test_daily_utc_cadence_covers_05_hour_in_edt_and_est():
    cron_minutes = (17, 47)
    cron_hours = range(9, 13)

    for day in ((2026, 7, 15), (2026, 12, 15)):
        local_times = [
            datetime(*day, hour, minute, tzinfo=timezone.utc).astimezone(TORONTO)
            for hour in cron_hours
            for minute in cron_minutes
        ]
        assert any(local.hour == 5 for local in local_times)

    summer_times = [
        datetime(2026, 7, 15, hour, minute, tzinfo=timezone.utc).astimezone(TORONTO)
        for hour in cron_hours
        for minute in cron_minutes
    ]
    winter_times = [
        datetime(2026, 12, 15, hour, minute, tzinfo=timezone.utc).astimezone(TORONTO)
        for hour in cron_hours
        for minute in cron_minutes
    ]
    assert min(local.hour for local in summer_times) <= 1
    assert min(local.hour for local in winter_times) <= 1
    assert any(local.hour < 5 for local in summer_times)
    assert any(local.hour < 5 for local in winter_times)


def test_daily_gate_uses_current_toronto_date_across_delayed_midnight_delivery():
    gate_script = named_step(load(BUILD), "Check whether today's edition already exists")["run"]
    nominal_slot = datetime(2026, 9, 16, 12, 47, tzinfo=timezone.utc).astimezone(TORONTO)
    delivered_before_05 = datetime(2026, 9, 17, 4, 30, tzinfo=TORONTO)
    delivered_after_05 = datetime(2026, 9, 17, 10, 20, tzinfo=TORONTO)

    assert nominal_slot.date() != delivered_before_05.date()
    assert (
        expected_daily_gate_outcome(
            event="schedule",
            local_hour=delivered_before_05.hour,
            edition_exists=False,
        )
        == "pre-05-scheduled-noop"
    )
    assert (
        expected_daily_gate_outcome(
            event="schedule",
            local_hour=delivered_after_05.hour,
            edition_exists=False,
        )
        == "build-required"
    )
    assert "TZ=America/Toronto date +%Y-%m-%d" in gate_script
    assert "github.event.schedule" not in gate_script


def test_morning_build_push_recovery_is_bounded_and_ignores_operational_paths():
    build_triggers = triggers(load(BUILD))
    push = build_triggers["push"]

    assert push["branches"] == ["main"]
    assert DAILY_PUSH_IGNORES <= set(push["paths-ignore"])

    gate_script = named_step(load(BUILD), "Check whether today's edition already exists")["run"]
    assert '"$EVENT" = "push"' in gate_script
    assert '"$LOCAL_HOUR" -lt 5' in gate_script
    assert '"$LOCAL_HOUR" -gt 11' in gate_script
    assert "push-window-noop" in gate_script


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
    assert "github.event_name" in gate_script
    assert "workflow_dispatch" not in gate_script
    assert "already-published-noop" in gate_script

    for step_name in ("Set up Python", "Install dependencies", "Build edition", "Commit and push"):
        index = next(
            index for index, step in enumerate(steps) if step.get("name") == step_name
        )
        assert index > gate_index
        assert steps[index]["if"] == "steps.gate.outputs.skip != 'true'"


def test_morning_build_exposes_explicit_publication_and_noop_outcomes():
    build = load(BUILD)
    gate_script = named_step(build, "Check whether today's edition already exists")["run"]
    publish_script = named_step(build, "Commit and push")["run"]
    report = named_step(build, "Report Daily outcome")

    for outcome in (
        "already-published-noop",
        "pre-05-scheduled-noop",
        "push-window-noop",
        "build-required",
    ):
        assert outcome in gate_script

    assert "outcome=published" in publish_script
    assert "outcome=build-failure" in publish_script
    assert "produced no docs/index.html change" in publish_script
    assert report["if"] == "always()"
    assert "$GITHUB_STEP_SUMMARY" in report["run"]
    assert "Daily run outcome" in report["run"]
    assert "Edition existed at gate" in report["run"]
    assert "Outcome:" in report["run"]
    assert "build-failure" in report["run"]


def test_morning_build_exposes_required_news_provider_keys():
    env = env_for(load(BUILD)["jobs"]["build"])

    assert "GEMINI_API_KEY" in env
    assert "GUARDIAN_API_KEY" in env
    assert "NYT_API_KEY" in env
    assert "PERIGON_API_KEY" in env


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
    assert '"$LAST" = "$TODAY"' in notify_script
    assert '"$COMMIT_EPOCH" -ge "$RUN_STARTED_EPOCH"' in notify_script


def test_morning_push_remains_one_plain_edition_notification():
    notify_script = script(load(NOTIFY))

    assert "Today's edition is ready." in notify_script
    assert "voice" not in notify_script.lower()
