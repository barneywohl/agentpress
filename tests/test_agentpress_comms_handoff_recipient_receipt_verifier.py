from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agentpress_comms_handoff_recipient_receipt_verifier.py"
OUT = "agentpress/evidence/agentpress-comms-handoff-recipient-receipt-verifier-wave93.json"
MD = "agentpress/evidence/agentpress-comms-handoff-recipient-receipt-verifier-wave93.md"
WAVE92 = "agentpress/evidence/agentpress-launchpad-comms-handoff-wave92.json"
WAVE92_MD = "agentpress/evidence/agentpress-launchpad-comms-handoff-wave92.md"


def load_module():
    spec = importlib.util.spec_from_file_location("agentpress_comms_handoff_recipient_receipt_verifier", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def seed_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    shutil.copy(SCRIPT, root / "scripts/agentpress_comms_handoff_recipient_receipt_verifier.py")
    shutil.copy(Path(__file__), root / "tests/test_agentpress_comms_handoff_recipient_receipt_verifier.py")
    (root / "agentpress/evidence").mkdir(parents=True)
    (root / "agentpress/onboarding").mkdir(parents=True)
    proof_docs = {
        "agentpress/onboarding/first-run-wizard.json": {"status": "needs_choice"},
        "agentpress/evidence/agent-facing-launchpad-recovery-card-wave91.json": {"status": "ok"},
        "agentpress/evidence/agent-facing-acceptance-harness-replay-wave90.json": {"status": "ok"},
    }
    for rel, doc in proof_docs.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(json.dumps(doc), encoding="utf-8")
    wave92 = {
        "status": "ok",
        "handoff_id": "wave92-handoff-739ca4be26f7a23b",
        "blockers": [],
        "public_actions_taken": [],
        "external_actions": [],
        "comms_hub_packet": {
            "recipient_ready": True,
            "recipient_message": {
                "copy_paste_commands": ["python3 scripts/agentpress.py launchpad --json", "npm run rc:agent-facing-launchpad-recovery-card --silent"],
                "proof_refs": list(proof_docs),
            },
        },
    }
    (root / WAVE92).write_text(json.dumps(wave92), encoding="utf-8")
    (root / WAVE92_MD).write_text("# wave92\n", encoding="utf-8")
    package = {
        "scripts": {
            "rc:agentpress-comms-handoff-recipient-receipt-verifier": "python3 scripts/agentpress_comms_handoff_recipient_receipt_verifier.py . --out agentpress/evidence/agentpress-comms-handoff-recipient-receipt-verifier-wave93.json --markdown-out agentpress/evidence/agentpress-comms-handoff-recipient-receipt-verifier-wave93.md --include-pack-check --json"
        },
        "files": [
            "scripts/agentpress_comms_handoff_recipient_receipt_verifier.py",
            "tests/test_agentpress_comms_handoff_recipient_receipt_verifier.py",
            OUT,
            MD,
            WAVE92,
            WAVE92_MD,
        ],
    }
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    return root


def test_valid_receipt_is_ok(tmp_path: Path):
    mod = load_module()
    doc = mod.build_receipt(seed_root(tmp_path))
    assert doc["status"] == "ok"
    ack = doc["simulated_recipient_acknowledgement"]
    assert ack["handoff_id"] == "wave92-handoff-739ca4be26f7a23b"
    assert ack["commands_run"]
    assert ack["result_status"] == "ok"
    assert "No secrets" in ack["redaction_attestation"]
    assert doc["public_actions_taken"] == []
    assert doc["external_actions"] == []


def test_missing_wave92_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    (root / WAVE92).unlink()
    doc = mod.build_receipt(root)
    assert doc["status"] == "blocked"
    assert any("wave92_missing" in b for b in doc["blockers"])


def test_blocked_wave92_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    wave92 = json.loads((root / WAVE92).read_text(encoding="utf-8"))
    wave92["status"] = "blocked"
    (root / WAVE92).write_text(json.dumps(wave92), encoding="utf-8")
    doc = mod.build_receipt(root)
    assert "wave92_status_not_ok" in doc["blockers"]


def test_unsafe_command_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    wave92 = json.loads((root / WAVE92).read_text(encoding="utf-8"))
    wave92["comms_hub_packet"]["recipient_message"]["copy_paste_commands"].append("git push origin main")
    (root / WAVE92).write_text(json.dumps(wave92), encoding="utf-8")
    doc = mod.build_receipt(root)
    assert any("unsafe_or_nonlocal_command" in b for b in doc["blockers"])


def test_missing_proof_ref_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    (root / "agentpress/evidence/agent-facing-launchpad-recovery-card-wave91.json").unlink()
    doc = mod.build_receipt(root)
    assert any("missing_or_invalid_proof_ref" in b for b in doc["blockers"])


def test_missing_ack_fields_are_detected(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    wave92 = json.loads((root / WAVE92).read_text(encoding="utf-8"))
    wave92["handoff_id"] = ""
    wave92["comms_hub_packet"]["recipient_message"]["copy_paste_commands"] = []
    (root / WAVE92).write_text(json.dumps(wave92), encoding="utf-8")
    doc = mod.build_receipt(root)
    assert any("ack_missing_required_field:handoff_id" in b for b in doc["blockers"])
    assert any("ack_missing_required_field:commands_run" in b for b in doc["blockers"])


def test_package_exclusion_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    package["files"].remove(OUT)
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    doc = mod.build_receipt(root)
    assert any(f"package_json_files_missing:{OUT}" == b for b in doc["blockers"])


def test_public_external_contamination_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    wave92 = json.loads((root / WAVE92).read_text(encoding="utf-8"))
    wave92["public_actions_taken"] = ["sent"]
    wave92["external_actions"] = ["email"]
    (root / WAVE92).write_text(json.dumps(wave92), encoding="utf-8")
    doc = mod.build_receipt(root)
    assert "wave92_public_actions_taken_not_empty" in doc["blockers"]
    assert "wave92_external_actions_not_empty" in doc["blockers"]


def test_cli_writes_json_and_markdown(tmp_path: Path):
    root = seed_root(tmp_path)
    proc = subprocess.run(["python3", str(root / "scripts/agentpress_comms_handoff_recipient_receipt_verifier.py"), str(root), "--json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads((root / OUT).read_text(encoding="utf-8"))
    assert data["kind"] == "agentpress_comms_handoff_recipient_receipt_verifier"
    assert (root / MD).exists()
