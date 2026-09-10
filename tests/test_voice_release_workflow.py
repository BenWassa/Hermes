"""#26 production wiring without coupling to Daily schedule tests."""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
WATCH = WORKFLOWS / "voice-watch.yml"
ROUNDUP = WORKFLOWS / "voice-roundup.yml"
BUILD = WORKFLOWS / "build.yml"
CI = WORKFLOWS / "ci.yml"
RELEASE_PAGE_GLOB = "docs/voices/articles/**"


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def script(workflow: dict) -> str:
    return "\n".join(
        step["run"]
        for job in workflow.get("jobs", {}).values()
        for step in job.get("steps", [])
        if isinstance(step, dict) and step.get("run")
    )


def env(workflow: dict) -> dict:
    out: dict = {}
    for job in workflow.get("jobs", {}).values():
        for step in job.get("steps", []):
            if isinstance(step, dict):
                out.update(step.get("env", {}))
    return out


def triggers(workflow: dict) -> dict:
    return workflow.get("on", workflow.get(True))


def test_release_alert_workflow_is_hourly_core_summary_job_not_daily_build():
    watch = load(WATCH)
    cron = [entry["cron"] for entry in triggers(watch)["schedule"]]
    variables = env(watch)
    commands = script(watch)

    assert cron == ["37 * * * *"]
    assert "GEMINI_API_KEY" in variables
    assert "NTFY_TOPIC" in variables
    assert "NYT_API_KEY" not in variables
    assert "src.voice_watch" in commands
    assert "src.voice_roundup" not in commands
    assert "src.build" not in commands


def test_release_alert_daily_and_roundup_writers_remain_independent():
    watch = load(WATCH)
    roundup = load(ROUNDUP)
    build = load(BUILD)

    groups = {
        watch["concurrency"]["group"],
        roundup["concurrency"]["group"],
        build["concurrency"]["group"],
    }
    assert len(groups) == 3
    assert watch["concurrency"]["cancel-in-progress"] is False
    assert roundup["concurrency"]["cancel-in-progress"] is False
    assert build["concurrency"]["cancel-in-progress"] is False

    roundup_commands = script(roundup)
    build_commands = script(build)
    assert "src.voice_watch" not in roundup_commands
    assert "src.voice_watch" not in build_commands


def test_generated_stable_article_pages_do_not_recursively_trigger_ci():
    ignored = set(triggers(load(CI))["push"]["paths-ignore"])
    assert RELEASE_PAGE_GLOB in ignored


def test_article_page_publisher_is_a_bounded_repo_writer():
    from src.voices.release import GitArticlePagePublisher

    publisher = GitArticlePagePublisher(attempts=3)
    assert publisher.attempts == 3
    assert hasattr(publisher, "publish")
