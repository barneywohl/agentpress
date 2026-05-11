from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.agentpress_gorilla_launchpad_acceptance_runbook import build_runbook, local_path_ok, safe_command

ROOT = Path(__file__).resolve().parents[1]


def test_local_path_and_command_guards_block_external_secret_public_actions() -> None:
    assert local_path_ok("agentpress/evidence/runbook.json")
    assert not local_path_ok("../runbook.json")
    assert not local_path_ok("https://example.com/runbook.json")
    assert not local_path_ok("agentpress/evidence/api-key-runbook.json")
    assert safe_command("echo local-only")
    assert not safe_command("curl https://example.com")
    assert not safe_command("npm publish")


def test_build_runbook_is_ready_and_preserves_jake_public_gate() -> None:
    data = build_runbook(ROOT)
    assert data["status"] == "ok"
    assert data["blockers"] == []
    assert data["public_push_publish_deploy"] is False
    assert data["external_actions"] == []
    assert data["payment_actions_taken"] == []
    assert data["jake_explicit_approval_required_for_public_actions"] is True
    assert data["one_first_command"].startswith("echo ")
    assert len(data["runbook_steps"]) == 5
    assert any(field["name"] == "operator_acknowledged_first_command" for field in data["operator_acknowledgement_fields"])
    assert "agentpress/evidence/agentpress-gorilla-receipt-acceptance-launchpad-packet-wave102.json" in data["handoff_ready_artifacts"]


def test_operator_template_and_criteria_are_handoff_ready() -> None:
    data = build_runbook(ROOT)
    template = data["operator_acknowledgement_template"]
    assert "operator_agent_id" in template
    assert template["criteria_checked"] == []
    assert any("stop before" in item for item in data["acceptance_criteria"])
    assert any("payment" in item.lower() for item in data["failure_stop_rules"])


def test_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    out = tmp_path / "runbook.json"
    md = tmp_path / "runbook.md"
    proc = subprocess.run(
        ["python3", "scripts/agentpress_gorilla_launchpad_acceptance_runbook.py", ".", "--out", str(out), "--markdown-out", str(md), "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    summary = json.loads(proc.stdout)
    assert summary["status"] == "ok"
    data = json.loads(out.read_text())
    assert data["status"] == "ok"
    assert md.read_text().startswith("# AgentPress Gorilla launchpad acceptance runbook")
