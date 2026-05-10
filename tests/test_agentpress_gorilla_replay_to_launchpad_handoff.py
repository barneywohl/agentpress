from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agentpress_gorilla_replay_to_launchpad_handoff.py"
OUT = "agentpress/evidence/agentpress-gorilla-replay-to-launchpad-handoff-wave98.json"
MD = "agentpress/evidence/agentpress-gorilla-replay-to-launchpad-handoff-wave98.md"
RECEIPT = "agentpress/evidence/agentpress-gorilla-replay-receipt-collector-wave97.json"
RECEIPT_MD = "agentpress/evidence/agentpress-gorilla-replay-receipt-collector-wave97.md"


def load_module():
    spec = importlib.util.spec_from_file_location("agentpress_gorilla_replay_to_launchpad_handoff", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def seed_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    shutil.copy(SCRIPT, root / "scripts/agentpress_gorilla_replay_to_launchpad_handoff.py")
    shutil.copy(Path(__file__), root / "tests/test_agentpress_gorilla_replay_to_launchpad_handoff.py")
    (root / "agentpress/evidence").mkdir(parents=True)
    receipt = {
        "kind": "agentpress_gorilla_replay_receipt_collector",
        "status": "ok",
        "receipt_id": "wave97-gorilla-replay-receipt-test",
        "source_replay_script": "agentpress/evidence/agentpress-gorilla-manifest-acceptance-harness-wave96-replay.sh",
        "replay_commands": [
            {"index": 1, "command": "echo 'AgentPress Gorilla manifest acceptance replay (local-only)'", "safe_local_only": True, "status": "ready_to_run_locally"},
            {"index": 2, "command": "python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json", "safe_local_only": True, "status": "ready_to_run_locally"},
            {"index": 3, "command": "python3 scripts/agentpress.py proof-capture --task-id glm-gorilla-bootstrap-conveyor --evidence-dir agentpress/gorilla/glm-bootstrap-conveyor-wave87-proof --artifacts agentpress/gorilla/glm-bootstrap-conveyor-wave87.json --commands 'python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json' --json", "safe_local_only": True, "status": "ready_to_run_locally"},
        ],
        "expected_local_artifacts_after_replay": ["agentpress/gorilla/utility-pack", "agentpress/gorilla/glm-bootstrap-conveyor-wave87-proof"],
        "public_actions_taken": [],
        "external_actions": [],
        "payment_actions_taken": [],
        "secret_material_included": False,
        "blockers": [],
    }
    (root / RECEIPT).write_text(json.dumps(receipt), encoding="utf-8")
    (root / RECEIPT_MD).write_text("# receipt\n", encoding="utf-8")
    package = {
        "scripts": {
            "rc:agentpress-gorilla-replay-to-launchpad-handoff": "python3 scripts/agentpress_gorilla_replay_to_launchpad_handoff.py . --out agentpress/evidence/agentpress-gorilla-replay-to-launchpad-handoff-wave98.json --markdown-out agentpress/evidence/agentpress-gorilla-replay-to-launchpad-handoff-wave98.md --include-pack-check --json"
        },
        "files": [
            "scripts/agentpress_gorilla_replay_to_launchpad_handoff.py",
            "tests/test_agentpress_gorilla_replay_to_launchpad_handoff.py",
            OUT,
            MD,
            RECEIPT,
            RECEIPT_MD,
        ],
    }
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    return root


def test_launchpad_handoff_is_ok(tmp_path: Path):
    mod = load_module()
    doc = mod.build_handoff(seed_root(tmp_path))
    assert doc["status"] == "ok"
    card = doc["launchpad_handoff_card"]
    assert card["card_id"].startswith("wave98-gorilla-launchpad-handoff-")
    assert card["source_receipt_id"] == "wave97-gorilla-replay-receipt-test"
    assert any(step["command"].startswith("python3 scripts/agentpress.py ") for step in card["first_run_steps"])
    assert all(step["safe_local_only"] for step in card["first_run_steps"])
    assert "agentpress/gorilla/utility-pack" in card["local_artifact_checks"]
    assert doc["public_actions_taken"] == []
    assert doc["external_actions"] == []
    assert doc["payment_actions_taken"] == []
    assert doc["secret_material_included"] is False


def test_receipt_blocker_blocks_handoff(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    receipt = json.loads((root / RECEIPT).read_text(encoding="utf-8"))
    receipt["blockers"] = ["unsafe"]
    (root / RECEIPT).write_text(json.dumps(receipt), encoding="utf-8")
    doc = mod.build_handoff(root)
    assert doc["status"] == "blocked"
    assert "receipt_blockers_not_empty" in doc["blockers"]


def test_unsafe_command_blocks_handoff(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    receipt = json.loads((root / RECEIPT).read_text(encoding="utf-8"))
    receipt["replay_commands"].append({"index": 4, "command": "npm publish --access public", "safe_local_only": True, "status": "ready_to_run_locally"})
    (root / RECEIPT).write_text(json.dumps(receipt), encoding="utf-8")
    doc = mod.build_handoff(root)
    assert any("receipt_replay_command_not_launchpad_safe" in b for b in doc["blockers"])


def test_missing_local_artifact_checks_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    receipt = json.loads((root / RECEIPT).read_text(encoding="utf-8"))
    receipt["expected_local_artifacts_after_replay"] = []
    (root / RECEIPT).write_text(json.dumps(receipt), encoding="utf-8")
    doc = mod.build_handoff(root)
    assert "handoff_missing_local_artifact_checks" in doc["blockers"]


def test_package_exclusion_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    package["files"].remove(RECEIPT_MD)
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    doc = mod.build_handoff(root)
    assert f"package_json_files_missing:{RECEIPT_MD}" in doc["blockers"]


def test_cli_writes_json_and_markdown(tmp_path: Path):
    root = seed_root(tmp_path)
    proc = subprocess.run(
        ["python3", str(root / "scripts/agentpress_gorilla_replay_to_launchpad_handoff.py"), str(root), "--json"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads((root / OUT).read_text(encoding="utf-8"))
    assert data["kind"] == "agentpress_gorilla_replay_to_launchpad_handoff"
    assert (root / MD).exists()
    assert "Jake explicit approval required" in (root / MD).read_text(encoding="utf-8")
