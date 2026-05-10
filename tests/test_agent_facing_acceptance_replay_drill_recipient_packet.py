import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_replay_drill_recipient_packet.py"
SOURCE_FILES = [
    "agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.json",
    "agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.md",
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
    "scripts/agent_facing_acceptance_handoff_capsule_replay_drill.py",
    "tests/test_agent_facing_acceptance_handoff_capsule_replay_drill.py",
    "scripts/agent_facing_acceptance_smoke_replay_receipt_verifier.py",
    "tests/test_agent_facing_acceptance_smoke_replay_receipt_verifier.py",
    "scripts/agent_facing_acceptance_smoke_replay_receipt.py",
    "tests/test_agent_facing_acceptance_smoke_replay_receipt.py",
]
OUT = "agentpress/evidence/agent-facing-acceptance-replay-drill-recipient-packet-wave86.json"
MD = "agentpress/evidence/agent-facing-acceptance-replay-drill-recipient-packet-wave86.md"


def copy_fixture_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for rel in SOURCE_FILES:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, target)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    shutil.copy(SCRIPT, root / "scripts/agent_facing_acceptance_replay_drill_recipient_packet.py")
    shutil.copy(Path(__file__), root / "tests/test_agent_facing_acceptance_replay_drill_recipient_packet.py")
    package = json.loads((ROOT / "package.json").read_text())
    package["scripts"] = {
        "rc:agent-facing-acceptance-replay-drill-recipient-packet": "python3 scripts/agent_facing_acceptance_replay_drill_recipient_packet.py . --out agentpress/evidence/agent-facing-acceptance-replay-drill-recipient-packet-wave86.json --markdown-out agentpress/evidence/agent-facing-acceptance-replay-drill-recipient-packet-wave86.md --include-pack-check --json",
        "rc:agent-facing-acceptance-smoke-replay-receipt-verifier": "python3 scripts/agent_facing_acceptance_smoke_replay_receipt_verifier.py . --out agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json --markdown-out agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.md --json",
    }
    package["files"] = sorted(set(package.get("files", [])) | set(SOURCE_FILES) | {
        "scripts/agent_facing_acceptance_replay_drill_recipient_packet.py",
        "tests/test_agent_facing_acceptance_replay_drill_recipient_packet.py",
        OUT,
        MD,
        "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json",
        "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.md",
        "scripts/agent_facing_acceptance_smoke_replay_receipt.py",
        "tests/test_agent_facing_acceptance_smoke_replay_receipt.py",
    })
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    return root


def run_packet(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(root / "scripts/agent_facing_acceptance_replay_drill_recipient_packet.py"), str(root), "--json", *extra],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def read_output(root: Path) -> dict:
    return json.loads((root / OUT).read_text())


def test_valid_packet_executes_same_single_safe_command(tmp_path):
    root = copy_fixture_tree(tmp_path)
    result = run_packet(root)
    assert result.returncode == 0, result.stderr + result.stdout
    data = read_output(root)
    packet = data["recipient_packet"]
    assert data["status"] == "ok"
    assert data["public_actions_taken"] == []
    assert data["external_actions"] == []
    assert packet["recommended_safe_paste_command_count"] == 1
    assert packet["safe_paste_commands"] == ["npm run rc:agent-facing-acceptance-smoke-replay-receipt-verifier --silent"]
    assert data["selected_command_run"]["returncode"] == 0
    assert data["packet_stop_go_coverage"]["missing"] == []
    assert data["operator_text_forbidden_hits"] == []
    assert len(packet["operator_instructions"]) >= 5


def test_blocks_missing_or_blocked_wave85(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / "agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.json"
    source = json.loads(path.read_text())
    source["status"] = "blocked"
    source["blockers"] = ["upstream failed"]
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_packet(root, "--skip-command-run")
    assert result.returncode == 2
    blockers = read_output(root)["blockers"]
    assert "wave85_status_not_ok: 'blocked'" in blockers
    assert "wave85_has_blockers" in blockers


def test_blocks_command_failure_or_unsafe_command(tmp_path):
    root = copy_fixture_tree(tmp_path)
    package = json.loads((root / "package.json").read_text())
    package["scripts"]["rc:agent-facing-acceptance-smoke-replay-receipt-verifier"] = "python3 -c 'import sys; sys.exit(7)'"
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    result = run_packet(root)
    assert result.returncode == 2
    assert "selected_command_replay_failed" in read_output(root)["blockers"]

    root = copy_fixture_tree(tmp_path / "unsafe")
    path = root / "agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.json"
    source = json.loads(path.read_text())
    source["replay_drill_receipt"]["selected_safe_paste_command"] = "git push origin main"
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_packet(root, "--skip-command-run")
    assert result.returncode == 2
    assert any("forbidden_operator_or_command_text_detected" in b for b in read_output(root)["blockers"])


def test_blocks_missing_criteria(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / "agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.json"
    source = json.loads(path.read_text())
    source["replay_drill_receipt"]["stop_go_coverage"]["missing"] = ["expected_output_count is at least 4"]
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_packet(root, "--skip-command-run")
    assert result.returncode == 2
    assert "wave85_missing_stop_go_coverage" in read_output(root)["blockers"]


def test_blocks_package_exclusion(tmp_path):
    root = copy_fixture_tree(tmp_path)
    package = json.loads((root / "package.json").read_text())
    package["files"] = [item for item in package["files"] if item != "scripts/agent_facing_acceptance_replay_drill_recipient_packet.py"]
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    result = run_packet(root, "--skip-command-run")
    assert result.returncode == 2
    assert "package_json_files_missing: scripts/agent_facing_acceptance_replay_drill_recipient_packet.py" in read_output(root)["blockers"]


def test_blocks_public_external_contamination(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / "agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.json"
    source = json.loads(path.read_text())
    source["public_actions_taken"] = ["posted"]
    source["external_actions"] = ["contacted"]
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_packet(root, "--skip-command-run")
    assert result.returncode == 2
    blockers = read_output(root)["blockers"]
    assert "wave85_public_actions_contaminated" in blockers
    assert "wave85_external_actions_contaminated" in blockers
