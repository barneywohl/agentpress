from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.agentpress_gorilla_launchpad_first_run_drill import build_drill, local_only

ROOT = Path(__file__).resolve().parents[1]


def test_local_only_rejects_public_and_network_commands() -> None:
    assert local_only("python3 scripts/agentpress.py launchpad --provider local --json")
    assert not local_only("git push origin main")
    assert not local_only("curl https://example.com")
    assert not local_only("npm publish")


def test_build_drill_from_wave98_handoff_is_ready() -> None:
    data = build_drill(ROOT)
    assert data["status"] == "ok"
    assert data["public_push_publish_deploy"] is False
    assert data["jake_explicit_approval_required_for_public_actions"] is True
    assert data["blockers"] == []
    steps = data["first_run_drill"]["steps"]
    assert steps
    assert all(step["safe_local_only"] for step in steps)
    assert all("exit_code" in data["first_run_drill"]["evidence_bundle_required"] for _ in steps)


def test_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    out = tmp_path / "drill.json"
    md = tmp_path / "drill.md"
    proc = subprocess.run(
        [
            "python3",
            "scripts/agentpress_gorilla_launchpad_first_run_drill.py",
            ".",
            "--out",
            str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out),
            "--markdown-out",
            str(md.relative_to(ROOT)) if md.is_relative_to(ROOT) else str(md),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text())
    assert data["status"] == "ok"
    assert md.read_text().startswith("# AgentPress Gorilla launchpad first-run drill")
