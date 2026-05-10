import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_smoke_replay_receipt_verifier.py"
SOURCE_FILES = [
    "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json",
    "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.md",
    "agentpress/evidence/agent-facing-acceptance-one-command-smoke-packet-wave81.json",
    "agentpress/evidence/agent-facing-acceptance-first-command-dry-run-wave80.json",
    "agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.json",
    "agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.md",
    "scripts/agent_facing_acceptance_smoke_replay_receipt.py",
    "tests/test_agent_facing_acceptance_smoke_replay_receipt.py",
]
OUT = "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json"
MD = "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.md"


def copy_fixture_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for rel in SOURCE_FILES:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, target)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    shutil.copy(SCRIPT, root / "scripts/agent_facing_acceptance_smoke_replay_receipt_verifier.py")
    shutil.copy(Path(__file__), root / "tests/test_agent_facing_acceptance_smoke_replay_receipt_verifier.py")
    package = json.loads((ROOT / "package.json").read_text())
    package["scripts"] = {
        "rc:agent-facing-acceptance-smoke-replay-receipt-verifier": "python3 scripts/agent_facing_acceptance_smoke_replay_receipt_verifier.py . --out agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json --markdown-out agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.md --include-pack-check --json"
    }
    package["files"] = sorted(set(package.get("files", [])) | {
        "scripts/agent_facing_acceptance_smoke_replay_receipt_verifier.py",
        "tests/test_agent_facing_acceptance_smoke_replay_receipt_verifier.py",
        OUT,
        MD,
        "scripts/agent_facing_acceptance_smoke_replay_receipt.py",
        "tests/test_agent_facing_acceptance_smoke_replay_receipt.py",
        "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json",
        "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.md",
    })
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    return root


def run_verifier(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(root / "scripts/agent_facing_acceptance_smoke_replay_receipt_verifier.py"), str(root), "--json", *extra],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def read_output(root: Path) -> dict:
    return json.loads((root / OUT).read_text())


def test_valid_wave82_emits_wave83_certificate(tmp_path):
    root = copy_fixture_tree(tmp_path)
    result = run_verifier(root)
    assert result.returncode == 0, result.stderr + result.stdout
    data = read_output(root)
    assert data["status"] == "ok"
    assert data["public_actions_taken"] == []
    assert data["external_actions"] == []
    assert data["operator_certificate"]["certificate_id"].startswith("wave83-verifier-")
    assert data["operator_certificate"]["source_receipt_id"].startswith("wave82-smoke-replay-")
    assert data["operator_certificate"]["command_chain_verified"] is True


def test_blocks_missing_or_blocked_wave82(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json"
    source = json.loads(path.read_text())
    source["status"] = "blocked"
    source["blockers"] = ["upstream failed"]
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_verifier(root)
    assert result.returncode == 2
    data = read_output(root)
    assert "wave82_status_not_ok: 'blocked'" in data["blockers"]
    assert "wave82_has_blockers" in data["blockers"]


def test_blocks_replay_returncode_failure(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json"
    source = json.loads(path.read_text())
    source["selected_command_replay"]["returncode"] = 1
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_verifier(root)
    assert result.returncode == 2
    assert "wave82_selected_command_replay_returncode_not_zero" in read_output(root)["blockers"]


def test_blocks_command_mismatch(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / "agentpress/evidence/agent-facing-acceptance-one-command-smoke-packet-wave81.json"
    source = json.loads(path.read_text())
    source["selected_command"] = "npm run rc:agent-facing-acceptance-first-command-dry-run"
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_verifier(root)
    assert result.returncode == 2
    assert any("command_consistency_failed" in b for b in read_output(root)["blockers"])


def test_blocks_missing_expected_output(tmp_path):
    root = copy_fixture_tree(tmp_path)
    (root / "agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.md").unlink()
    result = run_verifier(root)
    assert result.returncode == 2
    assert "wave82_expected_output_missing_local: agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.md" in read_output(root)["blockers"]


def test_blocks_forbidden_command_and_public_external_contamination(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json"
    source = json.loads(path.read_text())
    source["public_actions_taken"] = ["npm publish"]
    source["external_actions"] = ["email sent"]
    source["selected_command"] = "git push origin main"
    source["packet_command_safety"][0]["command"] = "npm publish"
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_verifier(root)
    assert result.returncode == 2
    blockers = read_output(root)["blockers"]
    assert "wave82_public_actions_contaminated" in blockers
    assert "wave82_external_actions_contaminated" in blockers
    assert any("forbidden_command_text_detected" in b for b in blockers)


def test_blocks_source_pack_missing_required_file(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json"
    source = json.loads(path.read_text())
    source["npm_pack_dry_run"]["required_included"][0]["included"] = False
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_verifier(root)
    assert result.returncode == 2
    assert any("wave82_source_pack_missing_required" in b for b in read_output(root)["blockers"])
