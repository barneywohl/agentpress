import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_verifier_handoff_capsule.py"
SOURCE_FILES = [
    "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json",
    "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.md",
    "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json",
    "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.md",
    "agentpress/evidence/agent-facing-acceptance-one-command-smoke-packet-wave81.json",
    "agentpress/evidence/agent-facing-acceptance-first-command-dry-run-wave80.json",
    "agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.json",
    "agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.md",
    "scripts/agent_facing_acceptance_smoke_replay_receipt_verifier.py",
    "tests/test_agent_facing_acceptance_smoke_replay_receipt_verifier.py",
]
OUT = "agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.json"
MD = "agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.md"


def copy_fixture_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for rel in SOURCE_FILES:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, target)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    shutil.copy(SCRIPT, root / "scripts/agent_facing_acceptance_verifier_handoff_capsule.py")
    shutil.copy(Path(__file__), root / "tests/test_agent_facing_acceptance_verifier_handoff_capsule.py")
    package = json.loads((ROOT / "package.json").read_text())
    package["scripts"] = {
        "rc:agent-facing-acceptance-verifier-handoff-capsule": "python3 scripts/agent_facing_acceptance_verifier_handoff_capsule.py . --out agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.json --markdown-out agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.md --include-pack-check --json",
        "rc:agent-facing-acceptance-smoke-replay-receipt-verifier": "python3 scripts/agent_facing_acceptance_smoke_replay_receipt_verifier.py . --out agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json --markdown-out agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.md --json",
    }
    package["files"] = sorted(set(package.get("files", [])) | {
        "scripts/agent_facing_acceptance_verifier_handoff_capsule.py",
        "tests/test_agent_facing_acceptance_verifier_handoff_capsule.py",
        OUT,
        MD,
        "scripts/agent_facing_acceptance_smoke_replay_receipt_verifier.py",
        "tests/test_agent_facing_acceptance_smoke_replay_receipt_verifier.py",
        "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json",
        "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.md",
    })
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    return root


def run_capsule(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(root / "scripts/agent_facing_acceptance_verifier_handoff_capsule.py"), str(root), "--json", *extra],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def read_output(root: Path) -> dict:
    return json.loads((root / OUT).read_text())


def test_valid_capsule_has_single_safe_command_and_stop_go(tmp_path):
    root = copy_fixture_tree(tmp_path)
    result = run_capsule(root)
    assert result.returncode == 0, result.stderr + result.stdout
    data = read_output(root)
    capsule = data["handoff_capsule"]
    assert data["status"] == "ok"
    assert data["public_actions_taken"] == []
    assert data["external_actions"] == []
    assert capsule["command_chain_verified"] is True
    assert capsule["selected_command_replay_returncode"] == 0
    assert capsule["expected_output_count"] >= 4
    assert capsule["recommended_safe_paste_command_count"] == 1
    assert capsule["recommended_safe_paste_commands"][0]["command"] == "npm run rc:agent-facing-acceptance-smoke-replay-receipt-verifier --silent"
    assert len(capsule["fresh_agent_inspection_files"]) >= 5
    assert capsule["stop_go_criteria"]["go_if"]
    assert capsule["stop_go_criteria"]["stop_if"]


def test_blocks_missing_or_blocked_wave83(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json"
    source = json.loads(path.read_text())
    source["status"] = "blocked"
    source["blockers"] = ["upstream failed"]
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_capsule(root, "--skip-verifier-run")
    assert result.returncode == 2
    blockers = read_output(root)["blockers"]
    assert "wave83_status_not_ok: 'blocked'" in blockers
    assert "wave83_has_blockers" in blockers


def test_blocks_verifier_command_failure(tmp_path):
    root = copy_fixture_tree(tmp_path)
    package = json.loads((root / "package.json").read_text())
    package["scripts"]["rc:agent-facing-acceptance-smoke-replay-receipt-verifier"] = "python3 -c 'import sys; sys.exit(7)'"
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    result = run_capsule(root)
    assert result.returncode == 2
    assert "verifier_command_failed" in read_output(root)["blockers"]


def test_blocks_forbidden_command_text(tmp_path, monkeypatch):
    root = copy_fixture_tree(tmp_path)
    script = root / "scripts/agent_facing_acceptance_verifier_handoff_capsule.py"
    text = script.read_text()
    text = text.replace("npm run rc:agent-facing-acceptance-smoke-replay-receipt-verifier --silent", "git push origin main")
    script.write_text(text)
    result = run_capsule(root, "--skip-verifier-run")
    assert result.returncode == 2
    assert any("forbidden_command_text_detected" in b for b in read_output(root)["blockers"])


def test_blocks_missing_source_evidence(tmp_path):
    root = copy_fixture_tree(tmp_path)
    (root / "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json").unlink()
    result = run_capsule(root, "--skip-verifier-run")
    assert result.returncode == 2
    assert any("wave82_source_missing" in b for b in read_output(root)["blockers"])
    assert any("inspection_file_missing" in b for b in read_output(root)["blockers"])


def test_blocks_package_exclusion(tmp_path):
    root = copy_fixture_tree(tmp_path)
    package = json.loads((root / "package.json").read_text())
    package["files"] = [item for item in package["files"] if item != "scripts/agent_facing_acceptance_verifier_handoff_capsule.py"]
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    result = run_capsule(root, "--skip-verifier-run")
    assert result.returncode == 2
    assert "package_json_files_missing: scripts/agent_facing_acceptance_verifier_handoff_capsule.py" in read_output(root)["blockers"]


def test_blocks_public_external_contamination(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json"
    source = json.loads(path.read_text())
    source["public_actions_taken"] = ["posted"]
    source["external_actions"] = ["contacted"]
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_capsule(root, "--skip-verifier-run")
    assert result.returncode == 2
    blockers = read_output(root)["blockers"]
    assert "wave83_public_actions_contaminated" in blockers
    assert "wave83_external_actions_contaminated" in blockers
