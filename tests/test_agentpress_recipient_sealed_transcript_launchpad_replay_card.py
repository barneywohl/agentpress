from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agentpress_recipient_sealed_transcript_launchpad_replay_card.py"
OUT = "agentpress/evidence/agentpress-recipient-sealed-transcript-launchpad-replay-card-wave95.json"
MD = "agentpress/evidence/agentpress-recipient-sealed-transcript-launchpad-replay-card-wave95.md"
WAVE94 = "agentpress/evidence/agentpress-recipient-command-transcript-sealer-wave94.json"
WAVE94_MD = "agentpress/evidence/agentpress-recipient-command-transcript-sealer-wave94.md"


def load_module():
    spec = importlib.util.spec_from_file_location("agentpress_recipient_sealed_transcript_launchpad_replay_card", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def seed_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    shutil.copy(SCRIPT, root / "scripts/agentpress_recipient_sealed_transcript_launchpad_replay_card.py")
    shutil.copy(Path(__file__), root / "tests/test_agentpress_recipient_sealed_transcript_launchpad_replay_card.py")
    (root / "agentpress/evidence").mkdir(parents=True)
    wave94 = {
        "kind": "agentpress_recipient_command_transcript_sealer",
        "status": "ok",
        "source_handoff_id": "wave92-handoff-739ca4be26f7a23b",
        "blockers": [],
        "public_actions_taken": [],
        "external_actions": [],
        "recipient_command_transcript_seal": {
            "source_handoff_id": "wave92-handoff-739ca4be26f7a23b",
            "redaction_attestation": "No secrets, tokens, credentials, customer data, outreach payloads, or external messages included.",
            "transcript_steps": [
                {"step": 1, "command": "python3 scripts/agentpress.py launchpad --json", "source_status": "ok", "sealed_status": "sealed-ok", "safe_local_only": True},
                {"step": 2, "command": "npm run rc:agent-facing-launchpad-recovery-card --silent", "source_status": "ok", "sealed_status": "sealed-ok", "safe_local_only": True},
            ],
        },
    }
    (root / WAVE94).write_text(json.dumps(wave94), encoding="utf-8")
    (root / WAVE94_MD).write_text("# wave94\n", encoding="utf-8")
    package = {
        "scripts": {
            "rc:agentpress-recipient-sealed-transcript-launchpad-replay-card": "python3 scripts/agentpress_recipient_sealed_transcript_launchpad_replay_card.py . --out agentpress/evidence/agentpress-recipient-sealed-transcript-launchpad-replay-card-wave95.json --markdown-out agentpress/evidence/agentpress-recipient-sealed-transcript-launchpad-replay-card-wave95.md --include-pack-check --json"
        },
        "files": [
            "scripts/agentpress_recipient_sealed_transcript_launchpad_replay_card.py",
            "tests/test_agentpress_recipient_sealed_transcript_launchpad_replay_card.py",
            OUT,
            MD,
            WAVE94,
            WAVE94_MD,
        ],
    }
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    return root


def test_valid_wave94_builds_one_card(tmp_path: Path):
    mod = load_module()
    doc = mod.build_card(seed_root(tmp_path))
    assert doc["status"] == "ok"
    card = doc["launchpad_replay_card"]
    assert card["source_handoff_id"] == "wave92-handoff-739ca4be26f7a23b"
    assert card["card_id"].startswith("wave95-recipient-launchpad-replay-card-")
    assert len(card["one_card_replay_steps"]) == 2
    assert all(row["expected_result"] == "local-ready" for row in card["one_card_replay_steps"])
    assert doc["public_actions_taken"] == []
    assert doc["external_actions"] == []


def test_missing_wave94_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    (root / WAVE94).unlink()
    doc = mod.build_card(root)
    assert doc["status"] == "blocked"
    assert any("wave94_missing" in b for b in doc["blockers"])


def test_blocked_wave94_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    wave94 = json.loads((root / WAVE94).read_text(encoding="utf-8"))
    wave94["status"] = "blocked"
    (root / WAVE94).write_text(json.dumps(wave94), encoding="utf-8")
    doc = mod.build_card(root)
    assert "wave94_status_not_ok" in doc["blockers"]


def test_unsealed_step_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    wave94 = json.loads((root / WAVE94).read_text(encoding="utf-8"))
    wave94["recipient_command_transcript_seal"]["transcript_steps"][0]["sealed_status"] = "blocked"
    (root / WAVE94).write_text(json.dumps(wave94), encoding="utf-8")
    doc = mod.build_card(root)
    assert "wave94_step_not_sealed_ok:1" in doc["blockers"]


def test_unsafe_command_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    wave94 = json.loads((root / WAVE94).read_text(encoding="utf-8"))
    wave94["recipient_command_transcript_seal"]["transcript_steps"].append({"command": "npm publish --access public", "sealed_status": "sealed-ok", "safe_local_only": True})
    (root / WAVE94).write_text(json.dumps(wave94), encoding="utf-8")
    doc = mod.build_card(root)
    assert any("wave94_step_unsafe_or_nonlocal" in b for b in doc["blockers"])


def test_public_external_contamination_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    wave94 = json.loads((root / WAVE94).read_text(encoding="utf-8"))
    wave94["public_actions_taken"] = ["publish"]
    wave94["external_actions"] = ["email"]
    (root / WAVE94).write_text(json.dumps(wave94), encoding="utf-8")
    doc = mod.build_card(root)
    assert "wave94_public_actions_taken_not_empty" in doc["blockers"]
    assert "wave94_external_actions_not_empty" in doc["blockers"]


def test_package_exclusion_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    package["files"].remove(OUT)
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    doc = mod.build_card(root)
    assert any(f"package_json_files_missing:{OUT}" == b for b in doc["blockers"])


def test_cli_writes_json_and_markdown(tmp_path: Path):
    root = seed_root(tmp_path)
    proc = subprocess.run(["python3", str(root / "scripts/agentpress_recipient_sealed_transcript_launchpad_replay_card.py"), str(root), "--json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads((root / OUT).read_text(encoding="utf-8"))
    assert data["kind"] == "agentpress_recipient_sealed_transcript_launchpad_replay_card"
    assert (root / MD).exists()
