from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agentpress_recipient_command_transcript_sealer.py"
OUT = "agentpress/evidence/agentpress-recipient-command-transcript-sealer-wave94.json"
MD = "agentpress/evidence/agentpress-recipient-command-transcript-sealer-wave94.md"
WAVE93 = "agentpress/evidence/agentpress-comms-handoff-recipient-receipt-verifier-wave93.json"
WAVE93_MD = "agentpress/evidence/agentpress-comms-handoff-recipient-receipt-verifier-wave93.md"


def load_module():
    spec = importlib.util.spec_from_file_location("agentpress_recipient_command_transcript_sealer", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def seed_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    shutil.copy(SCRIPT, root / "scripts/agentpress_recipient_command_transcript_sealer.py")
    shutil.copy(Path(__file__), root / "tests/test_agentpress_recipient_command_transcript_sealer.py")
    (root / "agentpress/evidence").mkdir(parents=True)
    wave93 = {
        "status": "ok",
        "source_handoff_id": "wave92-handoff-739ca4be26f7a23b",
        "blockers": [],
        "public_actions_taken": [],
        "external_actions": [],
        "simulated_recipient_acknowledgement": {
            "handoff_id": "wave92-handoff-739ca4be26f7a23b",
            "result_status": "ok",
            "redaction_attestation": "No secrets, tokens, credentials, customer data, outreach payloads, or external messages included.",
            "commands_run": [
                {"command": "python3 scripts/agentpress.py launchpad --json", "mode": "simulated-local-verification", "status": "ok"},
                {"command": "npm run rc:agent-facing-launchpad-recovery-card --silent", "mode": "simulated-local-verification", "status": "ok"},
            ],
        },
    }
    (root / WAVE93).write_text(json.dumps(wave93), encoding="utf-8")
    (root / WAVE93_MD).write_text("# wave93\n", encoding="utf-8")
    package = {
        "scripts": {
            "rc:agentpress-recipient-command-transcript-sealer": "python3 scripts/agentpress_recipient_command_transcript_sealer.py . --out agentpress/evidence/agentpress-recipient-command-transcript-sealer-wave94.json --markdown-out agentpress/evidence/agentpress-recipient-command-transcript-sealer-wave94.md --include-pack-check --json"
        },
        "files": [
            "scripts/agentpress_recipient_command_transcript_sealer.py",
            "tests/test_agentpress_recipient_command_transcript_sealer.py",
            OUT,
            MD,
            WAVE93,
            WAVE93_MD,
        ],
    }
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    return root


def test_valid_wave93_seals_transcript(tmp_path: Path):
    mod = load_module()
    doc = mod.build_seal(seed_root(tmp_path))
    assert doc["status"] == "ok"
    seal = doc["recipient_command_transcript_seal"]
    assert seal["source_handoff_id"] == "wave92-handoff-739ca4be26f7a23b"
    assert len(seal["transcript_steps"]) == 2
    assert all(row["sealed_status"] == "sealed-ok" for row in seal["transcript_steps"])
    assert doc["public_actions_taken"] == []
    assert doc["external_actions"] == []


def test_missing_wave93_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    (root / WAVE93).unlink()
    doc = mod.build_seal(root)
    assert doc["status"] == "blocked"
    assert any("wave93_missing" in b for b in doc["blockers"])


def test_blocked_wave93_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    wave93 = json.loads((root / WAVE93).read_text(encoding="utf-8"))
    wave93["status"] = "blocked"
    (root / WAVE93).write_text(json.dumps(wave93), encoding="utf-8")
    doc = mod.build_seal(root)
    assert "wave93_status_not_ok" in doc["blockers"]


def test_unsafe_command_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    wave93 = json.loads((root / WAVE93).read_text(encoding="utf-8"))
    wave93["simulated_recipient_acknowledgement"]["commands_run"].append({"command": "git push origin main", "status": "ok"})
    (root / WAVE93).write_text(json.dumps(wave93), encoding="utf-8")
    doc = mod.build_seal(root)
    assert any("unsafe_or_nonlocal_command" in b for b in doc["blockers"])


def test_command_status_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    wave93 = json.loads((root / WAVE93).read_text(encoding="utf-8"))
    wave93["simulated_recipient_acknowledgement"]["commands_run"][0]["status"] = "blocked"
    (root / WAVE93).write_text(json.dumps(wave93), encoding="utf-8")
    doc = mod.build_seal(root)
    assert "wave93_command_status_not_ok:1" in doc["blockers"]


def test_public_external_contamination_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    wave93 = json.loads((root / WAVE93).read_text(encoding="utf-8"))
    wave93["public_actions_taken"] = ["publish"]
    wave93["external_actions"] = ["email"]
    (root / WAVE93).write_text(json.dumps(wave93), encoding="utf-8")
    doc = mod.build_seal(root)
    assert "wave93_public_actions_taken_not_empty" in doc["blockers"]
    assert "wave93_external_actions_not_empty" in doc["blockers"]


def test_package_exclusion_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    package["files"].remove(OUT)
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    doc = mod.build_seal(root)
    assert any(f"package_json_files_missing:{OUT}" == b for b in doc["blockers"])


def test_cli_writes_json_and_markdown(tmp_path: Path):
    root = seed_root(tmp_path)
    proc = subprocess.run(["python3", str(root / "scripts/agentpress_recipient_command_transcript_sealer.py"), str(root), "--json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads((root / OUT).read_text(encoding="utf-8"))
    assert data["kind"] == "agentpress_recipient_command_transcript_sealer"
    assert (root / MD).exists()
