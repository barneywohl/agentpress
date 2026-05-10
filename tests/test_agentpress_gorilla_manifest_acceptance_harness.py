from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agentpress_gorilla_manifest_acceptance_harness.py"
OUT = "agentpress/evidence/agentpress-gorilla-manifest-acceptance-harness-wave96.json"
MD = "agentpress/evidence/agentpress-gorilla-manifest-acceptance-harness-wave96.md"
REPLAY = "agentpress/evidence/agentpress-gorilla-manifest-acceptance-harness-wave96-replay.sh"
MANIFEST = "agentpress/gorilla/glm-bootstrap-conveyor-wave87.json"


def load_module():
    spec = importlib.util.spec_from_file_location("agentpress_gorilla_manifest_acceptance_harness", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def seed_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    shutil.copy(SCRIPT, root / "scripts/agentpress_gorilla_manifest_acceptance_harness.py")
    shutil.copy(Path(__file__), root / "tests/test_agentpress_gorilla_manifest_acceptance_harness.py")
    (root / "agentpress/gorilla").mkdir(parents=True)
    (root / "agentpress/evidence").mkdir(parents=True)
    manifest = {
        "schema_version": "2026-05-10.agentpress-glm-gorilla-bootstrap-conveyor.v1",
        "status": "ready",
        "first_useful_command": "python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json",
        "proof_command": "python3 scripts/agentpress.py proof-capture --task-id glm-gorilla-bootstrap-conveyor --evidence-dir agentpress/gorilla/glm-bootstrap-conveyor-wave87-proof --artifacts agentpress/gorilla/glm-bootstrap-conveyor-wave87.json --commands 'python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json' --json",
        "bootstrap_steps": [
            {"step": 1, "name": "inspect_receipt", "done": False, "fallback": "use local gorilla utility pack"},
            {"step": 2, "name": "run_first_useful_command", "command": "python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json"},
            {"step": 3, "name": "capture_proof", "command": "python3 scripts/agentpress.py proof-capture --task-id glm-gorilla-bootstrap-conveyor --evidence-dir agentpress/gorilla/glm-bootstrap-conveyor-wave87-proof --artifacts agentpress/gorilla/glm-bootstrap-conveyor-wave87.json --commands 'python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json' --json"},
        ],
        "safety": {
            "external_writes": False,
            "payments_attempted": False,
            "public_push_publish_deploy": False,
            "requires_human_approval_before_external_action": True,
        },
        "acceptance_gates": ["JSON packet generated", "no external action is performed"],
    }
    (root / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    package = {
        "scripts": {
            "rc:agentpress-gorilla-manifest-acceptance-harness": "python3 scripts/agentpress_gorilla_manifest_acceptance_harness.py . --out agentpress/evidence/agentpress-gorilla-manifest-acceptance-harness-wave96.json --markdown-out agentpress/evidence/agentpress-gorilla-manifest-acceptance-harness-wave96.md --include-pack-check --json"
        },
        "files": [
            "scripts/agentpress_gorilla_manifest_acceptance_harness.py",
            "tests/test_agentpress_gorilla_manifest_acceptance_harness.py",
            OUT,
            MD,
            REPLAY,
            MANIFEST,
        ],
    }
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    return root


def test_valid_manifest_builds_acceptance_harness(tmp_path: Path):
    mod = load_module()
    doc = mod.build_harness(seed_root(tmp_path))
    assert doc["status"] == "ok"
    harness = doc["acceptance_harness"]
    assert harness["harness_id"].startswith("wave96-gorilla-manifest-acceptance-")
    assert len(harness["acceptance_steps"]) == 3
    assert harness["acceptance_steps"][0]["execution_mode"] == "inspection-only"
    assert all(row["safe_local_only"] for row in harness["acceptance_steps"])
    assert doc["public_actions_taken"] == []
    assert doc["external_actions"] == []
    assert doc["payment_actions_taken"] == []
    assert doc["secret_material_included"] is False


def test_missing_manifest_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    (root / MANIFEST).unlink()
    doc = mod.build_harness(root)
    assert doc["status"] == "blocked"
    assert any("manifest_missing" in b for b in doc["blockers"])


def test_unsafe_first_command_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    manifest["first_useful_command"] = "npm publish --access public"
    (root / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    doc = mod.build_harness(root)
    assert "manifest_first_useful_command_unsafe_or_missing" in doc["blockers"]


def test_unsafe_step_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    manifest["bootstrap_steps"].append({"name": "bad", "command": "curl http://example.com"})
    (root / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    doc = mod.build_harness(root)
    assert any("manifest_step_unsafe_or_nonlocal" in b for b in doc["blockers"])


def test_safety_flags_required(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    manifest["safety"]["public_push_publish_deploy"] = True
    manifest["safety"]["requires_human_approval_before_external_action"] = False
    (root / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    doc = mod.build_harness(root)
    assert "manifest_safety_not_false:public_push_publish_deploy" in doc["blockers"]
    assert "manifest_missing_human_approval_gate" in doc["blockers"]


def test_package_exclusion_blocks(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    package["files"].remove(OUT)
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    doc = mod.build_harness(root)
    assert any(f"package_json_files_missing:{OUT}" == b for b in doc["blockers"])


def test_cli_writes_json_and_markdown(tmp_path: Path):
    root = seed_root(tmp_path)
    proc = subprocess.run(
        ["python3", str(root / "scripts/agentpress_gorilla_manifest_acceptance_harness.py"), str(root), "--json"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads((root / OUT).read_text(encoding="utf-8"))
    assert data["kind"] == "agentpress_gorilla_manifest_acceptance_harness"
    assert (root / MD).exists()
    replay = (root / REPLAY)
    assert replay.exists()
    text = replay.read_text(encoding="utf-8")
    assert "Local-only replay helper" in text
    assert "npm publish" not in text
    assert "Jake approval required" in text


def test_replay_script_contains_only_safe_allowlisted_commands(tmp_path: Path):
    mod = load_module()
    root = seed_root(tmp_path)
    doc = mod.build_harness(root)
    text = mod.replay_script(doc)
    assert "python3 scripts/agentpress.py gorilla-utility-pack" in text
    assert "python3 scripts/agentpress.py proof-capture" in text
    assert "curl http" not in text
    assert "npm publish" not in text
    assert "Jake approval required" in text
