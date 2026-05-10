import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_handoff_capsule_replay_drill.py"
SOURCE_FILES = [
    "agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.json",
    "agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.md",
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
OUT = "agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.json"
MD = "agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.md"


def copy_fixture_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for rel in SOURCE_FILES:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, target)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    shutil.copy(SCRIPT, root / "scripts/agent_facing_acceptance_handoff_capsule_replay_drill.py")
    shutil.copy(Path(__file__), root / "tests/test_agent_facing_acceptance_handoff_capsule_replay_drill.py")
    package = json.loads((ROOT / "package.json").read_text())
    package["scripts"] = {
        "rc:agent-facing-acceptance-handoff-capsule-replay-drill": "python3 scripts/agent_facing_acceptance_handoff_capsule_replay_drill.py . --out agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.json --markdown-out agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.md --include-pack-check --json",
        "rc:agent-facing-acceptance-smoke-replay-receipt-verifier": "python3 scripts/agent_facing_acceptance_smoke_replay_receipt_verifier.py . --out agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json --markdown-out agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.md --json",
    }
    package["files"] = sorted(set(package.get("files", [])) | {
        "scripts/agent_facing_acceptance_handoff_capsule_replay_drill.py",
        "tests/test_agent_facing_acceptance_handoff_capsule_replay_drill.py",
        OUT,
        MD,
        "scripts/agent_facing_acceptance_verifier_handoff_capsule.py",
        "tests/test_agent_facing_acceptance_verifier_handoff_capsule.py",
        "agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.json",
        "agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.md",
    })
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    return root


def run_drill(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(root / "scripts/agent_facing_acceptance_handoff_capsule_replay_drill.py"), str(root), "--json", *extra],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def read_output(root: Path) -> dict:
    return json.loads((root / OUT).read_text())


def test_valid_replay_receipt_executes_single_safe_command(tmp_path):
    root = copy_fixture_tree(tmp_path)
    result = run_drill(root)
    assert result.returncode == 0, result.stderr + result.stdout
    data = read_output(root)
    receipt = data["replay_drill_receipt"]
    assert data["status"] == "ok"
    assert data["public_actions_taken"] == []
    assert data["external_actions"] == []
    assert receipt["recommended_safe_paste_command_count"] == 1
    assert receipt["selected_safe_paste_command"] == "npm run rc:agent-facing-acceptance-smoke-replay-receipt-verifier --silent"
    assert receipt["selected_command_replay_returncode"] == 0
    assert receipt["command_chain_verified"] is True
    assert receipt["expected_output_count"] >= 4
    assert len(receipt["fresh_agent_inspection_files_verified"]) >= 5
    assert not receipt["stop_go_coverage"]["missing"]
    assert receipt["operator_text_forbidden_hits"] == []


def test_blocks_missing_or_blocked_wave84(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / "agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.json"
    source = json.loads(path.read_text())
    source["status"] = "blocked"
    source["blockers"] = ["upstream failed"]
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_drill(root, "--skip-command-run")
    assert result.returncode == 2
    blockers = read_output(root)["blockers"]
    assert "wave84_status_not_ok: 'blocked'" in blockers
    assert "wave84_has_blockers" in blockers


def test_blocks_command_failure(tmp_path):
    root = copy_fixture_tree(tmp_path)
    package = json.loads((root / "package.json").read_text())
    package["scripts"]["rc:agent-facing-acceptance-smoke-replay-receipt-verifier"] = "python3 -c 'import sys; sys.exit(7)'"
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    result = run_drill(root)
    assert result.returncode == 2
    assert "selected_command_replay_failed" in read_output(root)["blockers"]


def test_blocks_forbidden_command_text(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / "agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.json"
    source = json.loads(path.read_text())
    source["handoff_capsule"]["recommended_safe_paste_commands"][0]["command"] = "git push origin main"
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_drill(root, "--skip-command-run")
    assert result.returncode == 2
    assert any("forbidden_operator_or_command_text_detected" in b for b in read_output(root)["blockers"])


def test_blocks_missing_inspection_file(tmp_path):
    root = copy_fixture_tree(tmp_path)
    (root / "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json").unlink()
    result = run_drill(root, "--skip-command-run")
    assert result.returncode == 2
    assert any("inspection_file_missing" in b for b in read_output(root)["blockers"])


def test_blocks_missing_stop_go_criterion(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / "agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.json"
    source = json.loads(path.read_text())
    source["handoff_capsule"]["stop_go_criteria"] = {"go_if": ["wave83 status is ok"], "stop_if": []}
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_drill(root, "--skip-command-run")
    assert result.returncode == 2
    assert any("stop_go_criterion_missing" in b for b in read_output(root)["blockers"])


def test_blocks_package_exclusion(tmp_path):
    root = copy_fixture_tree(tmp_path)
    package = json.loads((root / "package.json").read_text())
    package["files"] = [item for item in package["files"] if item != "scripts/agent_facing_acceptance_handoff_capsule_replay_drill.py"]
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    result = run_drill(root, "--skip-command-run")
    assert result.returncode == 2
    assert "package_json_files_missing: scripts/agent_facing_acceptance_handoff_capsule_replay_drill.py" in read_output(root)["blockers"]


def test_blocks_public_external_contamination(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / "agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.json"
    source = json.loads(path.read_text())
    source["public_actions_taken"] = ["posted"]
    source["external_actions"] = ["contacted"]
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_drill(root, "--skip-command-run")
    assert result.returncode == 2
    blockers = read_output(root)["blockers"]
    assert "wave84_public_actions_contaminated" in blockers
    assert "wave84_external_actions_contaminated" in blockers
