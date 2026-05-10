from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agentpress_launchpad_comms_handoff.py"
OUT = "agentpress/evidence/agentpress-launchpad-comms-handoff-wave92.json"
MD = "agentpress/evidence/agentpress-launchpad-comms-handoff-wave92.md"


def load_module():
    spec = importlib.util.spec_from_file_location("agentpress_launchpad_comms_handoff", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def seed_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    shutil.copy(SCRIPT, root / "scripts/agentpress_launchpad_comms_handoff.py")
    shutil.copy(Path(__file__), root / "tests/test_agentpress_launchpad_comms_handoff.py")
    package = {
        "scripts": {
            "rc:agentpress-launchpad-comms-handoff": "python3 scripts/agentpress_launchpad_comms_handoff.py . --out agentpress/evidence/agentpress-launchpad-comms-handoff-wave92.json --markdown-out agentpress/evidence/agentpress-launchpad-comms-handoff-wave92.md --include-pack-check --json"
        },
        "files": [
            "scripts/agentpress_launchpad_comms_handoff.py",
            "tests/test_agentpress_launchpad_comms_handoff.py",
            OUT,
            MD,
        ],
    }
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    (root / "agentpress/onboarding").mkdir(parents=True)
    (root / "agentpress/onboarding/first-run-wizard.json").write_text(
        json.dumps({
            "status": "ok",
            "exact_next_command": "python3 scripts/agentpress.py doctor --json",
            "then_command": "python3 scripts/agentpress.py proof-capture --task-id first-run --json",
            "commands": {"launchpad": "python3 scripts/agentpress.py launchpad --json"},
        }),
        encoding="utf-8",
    )
    (root / "agentpress/evidence").mkdir(parents=True)
    (root / "agentpress/evidence/agent-facing-launchpad-recovery-card-wave91.json").write_text(
        json.dumps({"status": "ok", "safe_recovery_commands": ["npm run doctor --silent"]}), encoding="utf-8"
    )
    (root / "agentpress/evidence/agent-facing-acceptance-harness-replay-wave90.json").write_text(
        json.dumps({"status": "ok", "safe_paste_command": "npm run rc:agent-facing-acceptance-harness-replay-wave90 --silent"}),
        encoding="utf-8",
    )
    return root


def test_build_packet_is_recipient_ready(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    doc = mod.build_packet(root, include_pack=False)
    assert doc["status"] == "ok"
    assert doc["comms_hub_packet"]["recipient_ready"] is True
    assert doc["comms_hub_packet"]["recipient_message"]["copy_paste_commands"]
    assert doc["public_actions_taken"] == []
    assert doc["external_actions"] == []
    assert doc["proof_receipt_expectations"]["public_action_gate"] == "closed_until_jake_explicit_approval"


def test_cli_writes_json_and_markdown(tmp_path: Path):
    root = seed_root(tmp_path)
    proc = subprocess.run(
        ["python3", str(root / "scripts/agentpress_launchpad_comms_handoff.py"), str(root), "--json"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads((root / OUT).read_text(encoding="utf-8"))
    assert data["kind"] == "agentpress_launchpad_comms_handoff_packet"
    assert data["comms_hub_packet"]["recipient_message"]["message_type"] == "agentpress_launchpad_to_comms_hub_handoff"
    assert (root / MD).exists()


def test_unsafe_external_command_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    wizard = json.loads((root / "agentpress/onboarding/first-run-wizard.json").read_text(encoding="utf-8"))
    wizard["exact_next_command"] = "git push origin main"
    (root / "agentpress/onboarding/first-run-wizard.json").write_text(json.dumps(wizard), encoding="utf-8")
    doc = mod.build_packet(root, include_pack=False)
    assert doc["status"] == "blocked"
    assert any("unsafe_command_text_detected" in item for item in doc["blockers"])
