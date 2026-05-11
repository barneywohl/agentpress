from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.agentpress_gorilla_operator_acknowledgement_verifier import (
    build_verifier,
    example_acknowledgement,
    local_relative_path,
    validate_acknowledgement,
)
from scripts.agentpress_gorilla_launchpad_acceptance_runbook import build_runbook

ROOT = Path(__file__).resolve().parents[1]


def test_local_relative_path_guard_blocks_public_secret_paths() -> None:
    assert local_relative_path("agentpress/evidence/ack.json")
    assert not local_relative_path("../ack.json")
    assert not local_relative_path("/tmp/ack.json")
    assert not local_relative_path("https://example.com/ack.json")
    assert not local_relative_path("agentpress/evidence/api-key-ack.json")


def test_sample_acknowledgement_validates_against_wave103_runbook() -> None:
    runbook = build_runbook(ROOT)
    ack = example_acknowledgement(runbook)
    assert validate_acknowledgement(ack, runbook) == []
    assert ack["operator_acknowledged_first_command"] is True
    assert ack["first_command_exit_code"] == 0
    assert set(runbook["acceptance_criteria"]).issubset(set(ack["criteria_checked"]))


def test_bad_acknowledgement_fails_closed_with_stop_reason_requirement() -> None:
    runbook = build_runbook(ROOT)
    ack = example_acknowledgement(runbook)
    ack["operator_acknowledged_first_command"] = False
    ack["criteria_checked"] = []
    ack["generated_local_artifacts"] = ["https://example.com/exfil.json"]
    ack["stop_reason_if_blocked"] = ""
    blockers = validate_acknowledgement(ack, runbook)
    assert "ack_first_command_not_acknowledged" in blockers
    assert any(item.startswith("ack_criterion_unchecked:") for item in blockers)
    assert any(item.startswith("ack_artifact_not_local_relative:") for item in blockers)
    assert "ack_blocked_without_stop_reason" in blockers


def test_build_verifier_preserves_public_gate_and_handoff_artifacts() -> None:
    data = build_verifier(ROOT)
    assert data["status"] == "ok"
    assert data["blockers"] == []
    assert data["public_push_publish_deploy"] is False
    assert data["external_actions"] == []
    assert data["payment_actions_taken"] == []
    assert data["jake_explicit_approval_required_for_public_actions"] is True
    assert data["sample_validation_blockers"] == []
    assert len(data["verifier_steps"]) == 5
    assert "agentpress/evidence/agentpress-gorilla-launchpad-acceptance-runbook-wave103.json" in data["handoff_ready_artifacts"]


def test_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    out = tmp_path / "verifier.json"
    md = tmp_path / "verifier.md"
    proc = subprocess.run(
        ["python3", "scripts/agentpress_gorilla_operator_acknowledgement_verifier.py", ".", "--out", str(out), "--markdown-out", str(md), "--json"],
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
    assert md.read_text().startswith("# AgentPress Gorilla operator acknowledgement verifier")
