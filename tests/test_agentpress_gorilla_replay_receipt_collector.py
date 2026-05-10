from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agentpress_gorilla_replay_receipt_collector.py"
OUT = "agentpress/evidence/agentpress-gorilla-replay-receipt-collector-wave97.json"
MD = "agentpress/evidence/agentpress-gorilla-replay-receipt-collector-wave97.md"
HARNESS = "agentpress/evidence/agentpress-gorilla-manifest-acceptance-harness-wave96.json"
REPLAY = "agentpress/evidence/agentpress-gorilla-manifest-acceptance-harness-wave96-replay.sh"


def load_module():
    spec = importlib.util.spec_from_file_location("agentpress_gorilla_replay_receipt_collector", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def seed_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    shutil.copy(SCRIPT, root / "scripts/agentpress_gorilla_replay_receipt_collector.py")
    shutil.copy(Path(__file__), root / "tests/test_agentpress_gorilla_replay_receipt_collector.py")
    (root / "agentpress/evidence").mkdir(parents=True)
    harness = {
        "status": "ok",
        "acceptance_harness": {"local_replay_script": REPLAY},
        "public_actions_taken": [],
        "external_actions": [],
    }
    (root / HARNESS).write_text(json.dumps(harness), encoding="utf-8")
    replay = """#!/usr/bin/env bash
set -euo pipefail
# Local-only replay helper
# Jake explicit approval remains required before any public push/publish/deploy.
echo 'AgentPress Gorilla manifest acceptance replay (local-only)'
python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json
python3 scripts/agentpress.py proof-capture --task-id glm-gorilla-bootstrap-conveyor --evidence-dir agentpress/gorilla/glm-bootstrap-conveyor-wave87-proof --artifacts agentpress/gorilla/glm-bootstrap-conveyor-wave87.json --commands 'python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json' --json
"""
    (root / REPLAY).write_text(replay, encoding="utf-8")
    package = {
        "scripts": {
            "rc:agentpress-gorilla-replay-receipt-collector": "python3 scripts/agentpress_gorilla_replay_receipt_collector.py . --out agentpress/evidence/agentpress-gorilla-replay-receipt-collector-wave97.json --markdown-out agentpress/evidence/agentpress-gorilla-replay-receipt-collector-wave97.md --include-pack-check --json"
        },
        "files": [
            "scripts/agentpress_gorilla_replay_receipt_collector.py",
            "tests/test_agentpress_gorilla_replay_receipt_collector.py",
            OUT,
            MD,
            HARNESS,
            REPLAY,
        ],
    }
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    return root


def test_valid_replay_receipt_is_ok(tmp_path: Path):
    mod = load_module()
    doc = mod.build_receipt(seed_root(tmp_path))
    assert doc["status"] == "ok"
    assert doc["receipt_id"].startswith("wave97-gorilla-replay-receipt-")
    assert any(row["command"].startswith("python3 scripts/agentpress.py ") for row in doc["replay_commands"])
    assert all(row["safe_local_only"] for row in doc["replay_commands"])
    assert doc["public_actions_taken"] == []
    assert doc["external_actions"] == []
    assert doc["payment_actions_taken"] == []
    assert doc["secret_material_included"] is False


def test_missing_replay_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    (root / REPLAY).unlink()
    doc = mod.build_receipt(root)
    assert doc["status"] == "blocked"
    assert any("replay_missing" in b for b in doc["blockers"])


def test_unsafe_replay_command_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    with (root / REPLAY).open("a", encoding="utf-8") as handle:
        handle.write("npm publish --access public\n")
    doc = mod.build_receipt(root)
    assert any("replay_command_unsafe_or_nonlocal" in b for b in doc["blockers"])


def test_harness_status_must_be_ok(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    harness = json.loads((root / HARNESS).read_text(encoding="utf-8"))
    harness["status"] = "blocked"
    (root / HARNESS).write_text(json.dumps(harness), encoding="utf-8")
    doc = mod.build_receipt(root)
    assert "harness_status_not_ok" in doc["blockers"]


def test_package_exclusion_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    package["files"].remove(REPLAY)
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    doc = mod.build_receipt(root)
    assert f"package_json_files_missing:{REPLAY}" in doc["blockers"]


def test_cli_writes_json_and_markdown(tmp_path: Path):
    root = seed_root(tmp_path)
    proc = subprocess.run(
        ["python3", str(root / "scripts/agentpress_gorilla_replay_receipt_collector.py"), str(root), "--json"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads((root / OUT).read_text(encoding="utf-8"))
    assert data["kind"] == "agentpress_gorilla_replay_receipt_collector"
    assert (root / MD).exists()
    assert "Jake explicit approval required" in (root / MD).read_text(encoding="utf-8")
