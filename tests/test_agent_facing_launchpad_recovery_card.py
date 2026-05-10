import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_launchpad_recovery_card.py"
OUT = "agentpress/evidence/agent-facing-launchpad-recovery-card-wave91.json"
MD = "agentpress/evidence/agent-facing-launchpad-recovery-card-wave91.md"


def fixture_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    (root / "agentpress/onboarding").mkdir(parents=True)
    (root / "agentpress/evidence").mkdir(parents=True)
    shutil.copy(SCRIPT, root / "scripts/agent_facing_launchpad_recovery_card.py")
    shutil.copy(Path(__file__), root / "tests/test_agent_facing_launchpad_recovery_card.py")
    (root / "agentpress/onboarding/first-run-wizard.json").write_text(json.dumps({
        "status": "ready",
        "steps": [{"name": "doctor", "command": "npm run doctor --silent"}],
    }))
    (root / "agentpress/evidence/agent-facing-acceptance-harness-replay-wave90.json").write_text(json.dumps({
        "status": "ok",
        "safe_paste_command": "npm run rc:agent-facing-acceptance-smoke-replay-receipt-verifier --silent",
        "public_action_gate": "closed_until_jake_explicit_approval",
    }))
    package = {
        "name": "fixture",
        "version": "0.0.0",
        "scripts": {
            "doctor": "python3 -c 'print({})'",
            "rc:agent-facing-acceptance-harness-replay-wave90": "python3 -c 'print({})'",
            "rc:agent-facing-launchpad-recovery-card": "python3 scripts/agent_facing_launchpad_recovery_card.py . --out agentpress/evidence/agent-facing-launchpad-recovery-card-wave91.json --markdown-out agentpress/evidence/agent-facing-launchpad-recovery-card-wave91.md --include-pack-check --json",
        },
        "files": [
            "scripts/agent_facing_launchpad_recovery_card.py",
            "tests/test_agent_facing_launchpad_recovery_card.py",
            OUT,
            MD,
        ],
    }
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    return root


def run_card(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(root / "scripts/agent_facing_launchpad_recovery_card.py"), str(root), "--json", *extra],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def read_output(root: Path) -> dict:
    return json.loads((root / OUT).read_text())


def test_launchpad_recovery_card_emits_three_safe_local_commands(tmp_path):
    root = fixture_repo(tmp_path)
    result = run_card(root)
    assert result.returncode == 0, result.stderr + result.stdout
    data = read_output(root)
    assert data["status"] == "ok"
    assert data["public_actions_taken"] == []
    assert data["external_actions"] == []
    assert data["operator_decision_needed"] == "none_until_public_publish_or_push"
    assert data["safe_recovery_commands"] == [
        "npm run doctor --silent",
        "npm run rc:agent-facing-acceptance-harness-replay-wave90 --silent",
        "python3 scripts/agentpress.py launchpad --json",
    ]
    assert "reopen launchpad diagnostics" in data["agent_facing_outcome"]
    assert (root / MD).exists()


def test_blocks_missing_launchpad_wizard(tmp_path):
    root = fixture_repo(tmp_path)
    (root / "agentpress/onboarding/first-run-wizard.json").unlink()
    result = run_card(root)
    assert result.returncode == 2
    assert "launchpad_wizard_missing: agentpress/onboarding/first-run-wizard.json" in read_output(root)["blockers"]


def test_blocks_harness_replay_not_ok(tmp_path):
    root = fixture_repo(tmp_path)
    harness = root / "agentpress/evidence/agent-facing-acceptance-harness-replay-wave90.json"
    data = json.loads(harness.read_text())
    data["status"] = "blocked"
    harness.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    result = run_card(root)
    assert result.returncode == 2
    assert "acceptance_harness_status_not_ok: 'blocked'" in read_output(root)["blockers"]


def test_blocks_package_exclusion(tmp_path):
    root = fixture_repo(tmp_path)
    package = json.loads((root / "package.json").read_text())
    package["files"] = [item for item in package["files"] if item != "tests/test_agent_facing_launchpad_recovery_card.py"]
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    result = run_card(root)
    assert result.returncode == 2
    assert "package_json_files_missing: tests/test_agent_facing_launchpad_recovery_card.py" in read_output(root)["blockers"]
