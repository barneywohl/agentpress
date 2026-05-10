import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_harness_replay_matrix.py"
SOURCES = [
    "agentpress/evidence/rc-adoption-post-approval-cutover-rehearsal-wave69.json",
    "agentpress/evidence/rc-final-acceptance-snapshot-wave49.json",
    "agentpress/evidence/rc-public-action-guardrail-audit-wave52.json",
    "agentpress/evidence/rc-launch-signal-simulator-wave55.json",
    "agentpress/evidence/rc-adoption-route-run-receipt-collector-wave65.json",
]
OUT = "agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.json"


def copy_fixture_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "agentpress/evidence").mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    shutil.copy(SCRIPT, root / "scripts/agent_facing_acceptance_harness_replay_matrix.py")
    shutil.copy(Path(__file__), root / "tests/test_agent_facing_acceptance_harness_replay_matrix.py")
    for rel in SOURCES:
        shutil.copy(ROOT / rel, root / rel)
    package = json.loads((ROOT / "package.json").read_text())
    package["scripts"] = {
        "rc:agent-facing-acceptance-harness-replay-matrix": "python3 scripts/agent_facing_acceptance_harness_replay_matrix.py . --out agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.json --markdown-out agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.md --json"
    }
    package["files"] = list(set(package.get("files", [])) | {
        "scripts/agent_facing_acceptance_harness_replay_matrix.py",
        "tests/test_agent_facing_acceptance_harness_replay_matrix.py",
        "agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.json",
        "agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.md",
    })
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    return root


def run_matrix(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(root / "scripts/agent_facing_acceptance_harness_replay_matrix.py"), str(root), "--json", *extra],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def read_output(root: Path) -> dict:
    return json.loads((root / OUT).read_text())


def test_replay_matrix_valid_sources_covers_all_required_lanes_without_public_actions(tmp_path):
    root = copy_fixture_tree(tmp_path)
    result = run_matrix(root)
    assert result.returncode == 0, result.stderr + result.stdout
    data = read_output(root)
    assert data["status"] == "ok"
    assert data["public_actions_taken"] == []
    assert data["external_actions"] == []
    assert data["coverage"]["all_required_lanes_present"] is True
    lane_ids = {lane["id"] for lane in data["lanes"]}
    assert lane_ids == {
        "glm_gorilla_bootstrap_conveyor",
        "launchpad",
        "comms_hub",
        "marketplace",
        "safety_guardrails",
        "acceptance_harness",
    }
    assert all(lane["commands_executed"] is False for lane in data["lanes"])


def test_replay_matrix_blocks_missing_source_with_actionable_error(tmp_path):
    root = copy_fixture_tree(tmp_path)
    (root / SOURCES[1]).unlink()
    result = run_matrix(root)
    assert result.returncode == 2
    data = read_output(root)
    assert any("source_final_acceptance_snapshot_missing" in blocker for blocker in data["blockers"])
    assert data["public_actions_taken"] == []


def test_replay_matrix_blocks_source_public_actions_taken_fragment(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / SOURCES[2]
    payload = json.loads(path.read_text())
    payload["public_actions_taken"] = ["git push origin main"]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    result = run_matrix(root)
    assert result.returncode == 2
    data = read_output(root)
    assert "source_public_action_guardrail_audit_records_public_actions_taken" in data["blockers"]


def test_replay_matrix_blocks_status_not_ok_and_lane_coverage_gap(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / SOURCES[4]
    payload = json.loads(path.read_text())
    payload["status"] = "blocked"
    payload["blockers"] = ["synthetic route receipt failure"]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    result = run_matrix(root)
    assert result.returncode == 2
    data = read_output(root)
    assert "source_route_run_receipt_collector_status_not_ok: 'blocked'" in data["blockers"]
    assert data["coverage"]["all_required_lanes_present"] is False
    failed = [lane for lane in data["lanes"] if not lane["passed"]]
    assert any(lane["id"] == "glm_gorilla_bootstrap_conveyor" for lane in failed)


def test_markdown_lists_lanes_blockers_and_verification_commands(tmp_path):
    root = copy_fixture_tree(tmp_path)
    result = run_matrix(root)
    assert result.returncode == 0, result.stderr + result.stdout
    text = (root / "agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.md").read_text()
    assert "agent-facing acceptance harness replay matrix (wave70)" in text
    assert "GLM/gorilla bootstrap conveyor" in text
    assert "Comms hub" in text
    assert "Verification commands" in text
