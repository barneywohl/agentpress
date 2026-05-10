import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_harness_replay_wave90.py"
OUT = "agentpress/evidence/agent-facing-acceptance-harness-replay-wave90.json"
MD = "agentpress/evidence/agent-facing-acceptance-harness-replay-wave90.md"
SOURCE_PACKET = "agentpress/evidence/agent-facing-acceptance-replay-drill-recipient-packet-wave86.json"
SOURCE_PACKET_MD = "agentpress/evidence/agent-facing-acceptance-replay-drill-recipient-packet-wave86.md"


def fixture_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    shutil.copy(SCRIPT, root / "scripts/agent_facing_acceptance_harness_replay_wave90.py")
    shutil.copy(Path(__file__), root / "tests/test_agent_facing_acceptance_harness_replay_wave90.py")
    for rel in [SOURCE_PACKET, SOURCE_PACKET_MD]:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, target)
    for rel in [
        "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json",
        "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.md",
        "agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.json",
        "agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.md",
    ]:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, target)
    package = {
        "scripts": {
            "rc:agent-facing-acceptance-harness-replay-wave90": "python3 scripts/agent_facing_acceptance_harness_replay_wave90.py . --out agentpress/evidence/agent-facing-acceptance-harness-replay-wave90.json --markdown-out agentpress/evidence/agent-facing-acceptance-harness-replay-wave90.md --include-pack-check --json",
            "rc:agent-facing-acceptance-smoke-replay-receipt-verifier": "python3 -c 'import sys; sys.exit(0)'",
        },
        "files": [
            "scripts/agent_facing_acceptance_harness_replay_wave90.py",
            "tests/test_agent_facing_acceptance_harness_replay_wave90.py",
            OUT,
            MD,
            SOURCE_PACKET,
            SOURCE_PACKET_MD,
        ],
    }
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    return root


def run_harness(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(root / "scripts/agent_facing_acceptance_harness_replay_wave90.py"), str(root), "--json", *extra],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def read_output(root: Path) -> dict:
    return json.loads((root / OUT).read_text())


def test_replays_recipient_packet_and_writes_pass_fail_evidence(tmp_path):
    root = fixture_repo(tmp_path)
    result = run_harness(root)
    assert result.returncode == 0, result.stderr + result.stdout
    data = read_output(root)
    assert data["status"] == "ok"
    assert data["replay_result"]["returncode"] == 0
    assert data["public_actions_taken"] == []
    assert data["external_actions"] == []
    assert data["safe_paste_command"] == "npm run rc:agent-facing-acceptance-smoke-replay-receipt-verifier --silent"
    assert all(row["exists"] for row in data["expected_output_checks"])
    assert "pass/fail evidence" in data["painpoint_solved"]
    assert (root / MD).exists()


def test_blocks_failed_replay(tmp_path):
    root = fixture_repo(tmp_path)
    package = json.loads((root / "package.json").read_text())
    package["scripts"]["rc:agent-facing-acceptance-smoke-replay-receipt-verifier"] = "python3 -c 'import sys; sys.exit(9)'"
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    result = run_harness(root)
    assert result.returncode == 2
    assert "recipient_packet_replay_failed" in read_output(root)["blockers"]


def test_blocks_missing_expected_output(tmp_path):
    root = fixture_repo(tmp_path)
    (root / "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.md").unlink()
    result = run_harness(root, "--skip-replay")
    assert result.returncode == 2
    assert "expected_output_missing: agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.md" in read_output(root)["blockers"]


def test_blocks_unsafe_or_contaminated_packet(tmp_path):
    root = fixture_repo(tmp_path)
    packet_path = root / SOURCE_PACKET
    packet = json.loads(packet_path.read_text())
    packet["recipient_packet"]["safe_paste_commands"] = ["git push origin main"]
    packet["public_actions_taken"] = ["posted"]
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n")
    result = run_harness(root, "--skip-replay")
    blockers = read_output(root)["blockers"]
    assert result.returncode == 2
    assert "source_packet_public_external_contamination" in blockers
    assert any("forbidden_operator_or_command_text_detected" in b for b in blockers)


def test_blocks_package_exclusion(tmp_path):
    root = fixture_repo(tmp_path)
    package = json.loads((root / "package.json").read_text())
    package["files"] = [item for item in package["files"] if item != "tests/test_agent_facing_acceptance_harness_replay_wave90.py"]
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    result = run_harness(root, "--skip-replay")
    assert result.returncode == 2
    assert "package_json_files_missing: tests/test_agent_facing_acceptance_harness_replay_wave90.py" in read_output(root)["blockers"]
