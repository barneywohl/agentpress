from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.agentpress_gorilla_drill_evidence_capsule import build_capsule, safe_command, sha256_text

ROOT = Path(__file__).resolve().parents[1]


def test_safe_command_rejects_public_network_and_secret_actions() -> None:
    assert safe_command("python3 scripts/agentpress.py gorilla-utility-pack --json")
    assert safe_command("echo 'local drill receipt'")
    assert not safe_command("git push origin main")
    assert not safe_command("npm publish")
    assert not safe_command("curl https://example.com")
    assert not safe_command("echo token=abc")


def test_build_capsule_from_wave99_drill_is_ready() -> None:
    data = build_capsule(ROOT)
    assert data["status"] == "ok"
    assert data["public_push_publish_deploy"] is False
    assert data["jake_explicit_approval_required_for_public_actions"] is True
    assert data["blockers"] == []
    slots = data["evidence_slots"]
    assert slots
    assert all(slot["safe_local_only"] for slot in slots)
    assert all(slot["receipt_template"]["command_sha256"] == sha256_text(slot["command"]) for slot in slots)
    assert "public_action_attestation" in data["receipt_schema"]["required_top_level_fields"]


def test_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    out = tmp_path / "capsule.json"
    md = tmp_path / "capsule.md"
    proc = subprocess.run(
        [
            "python3",
            "scripts/agentpress_gorilla_drill_evidence_capsule.py",
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
    assert md.read_text().startswith("# AgentPress Gorilla drill evidence capsule")
