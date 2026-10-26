"""Gate the inert independent scheduler implementation in normal Python CI."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "ops" / "external-dispatch"


def test_cloudflare_worker_contract_and_node_fixtures():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node executable unavailable; test worker locally with node --test")
    result = subprocess.run(
        [node, "--test", str(WORKER / "worker.test.mjs")],
        cwd=ROOT, text=True, capture_output=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr


def test_independent_dispatch_is_inert_until_external_account_configured():
    conf = (WORKER / "wrangler.toml").read_text(encoding="utf-8")
    code = (WORKER / "worker.mjs").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")

    assert 'workers_dev = false' in conf
    assert 'crons = ["35,50 9,10 * * *"]' in conf
    assert "async scheduled(controller, env)" in code
    assert "async fetch(" not in code  # no callable public web endpoint
    assert "GITHUB_DISPATCH_TOKEN" in code and "GITHUB_DISPATCH_TOKEN" not in conf
    assert "workflow_dispatch:" in workflow
    assert "trigger_source:" in workflow
    assert "Dispatch label:" in workflow
    assert "group: build-the-daily" in workflow
    assert "Check whether today's edition already exists" in workflow
    assert "cancel-in-progress: false" in workflow
