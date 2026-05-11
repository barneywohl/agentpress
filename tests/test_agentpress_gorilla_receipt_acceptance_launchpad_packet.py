from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.agentpress_gorilla_receipt_acceptance_launchpad_packet import build_acceptance_packet, first_safe_command, local_path_ok

ROOT = Path(__file__).resolve().parents[1]


def test_local_path_guard_blocks_external_secret_and_parent_paths() -> None:
    assert local_path_ok("agentpress/evidence/receipt.json")
    assert not local_path_ok("https://example.com/receipt.json")
    assert not local_path_ok("../receipt.json")
    assert not local_path_ok("/tmp/receipt.json")
    assert not local_path_ok("agentpress/evidence/api-key-receipt.json")


def test_first_safe_command_uses_wave99_local_step() -> None:
    drill = json.loads((ROOT / "agentpress/evidence/agentpress-gorilla-launchpad-first-run-drill-wave99.json").read_text())
    cmd = first_safe_command(drill)
    assert cmd.startswith("echo ")
    assert "publish" not in cmd.lower()


def test_build_acceptance_packet_is_ready_and_preserves_public_gate() -> None:
    data = build_acceptance_packet(ROOT)
    assert data["status"] == "ok"
    assert data["blockers"] == []
    assert data["public_push_publish_deploy"] is False
    assert data["jake_explicit_approval_required_for_public_actions"] is True
    assert data["receipt_acceptance"]["all_steps_verified"] is True
    assert data["launchpad"]["first_command"]
    assert any("stop before" in item for item in data["launchpad"]["acceptance_criteria"])


def test_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    out = tmp_path / "packet.json"
    md = tmp_path / "packet.md"
    proc = subprocess.run(
        ["python3", "scripts/agentpress_gorilla_receipt_acceptance_launchpad_packet.py", ".", "--out", str(out), "--markdown-out", str(md), "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text())
    assert data["status"] == "ok"
    assert md.read_text().startswith("# AgentPress Gorilla receipt acceptance launchpad packet")
