import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_replay_operator_capsule.py"
MATRIX = "agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.json"
OUT = "agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.json"


def copy_fixture_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "agentpress/evidence").mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    shutil.copy(SCRIPT, root / "scripts/agent_facing_acceptance_replay_operator_capsule.py")
    shutil.copy(Path(__file__), root / "tests/test_agent_facing_acceptance_replay_operator_capsule.py")
    shutil.copy(ROOT / MATRIX, root / MATRIX)
    package = json.loads((ROOT / "package.json").read_text())
    package["scripts"] = {
        "rc:agent-facing-acceptance-replay-operator-capsule": "python3 scripts/agent_facing_acceptance_replay_operator_capsule.py . --out agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.json --markdown-out agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.md --json"
    }
    package["files"] = list(set(package.get("files", [])) | {
        "scripts/agent_facing_acceptance_replay_operator_capsule.py",
        "tests/test_agent_facing_acceptance_replay_operator_capsule.py",
        "agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.json",
        "agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.md",
    })
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    return root


def run_capsule(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(root / "scripts/agent_facing_acceptance_replay_operator_capsule.py"), str(root), "--json", *extra],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def read_output(root: Path) -> dict:
    return json.loads((root / OUT).read_text())


def test_operator_capsule_valid_matrix_summarizes_all_six_lanes_without_public_actions(tmp_path):
    root = copy_fixture_tree(tmp_path)
    result = run_capsule(root)
    assert result.returncode == 0, result.stderr + result.stdout
    data = read_output(root)
    assert data["status"] == "ok"
    assert data["public_actions_taken"] == []
    assert data["external_actions"] == []
    assert data["lane_count"] == 6
    assert {lane["id"] for lane in data["lane_summaries"]} == set(data["required_lane_ids"])
    assert all(lane["passed"] is True for lane in data["lane_summaries"])
    assert any("Do not publish" in item for item in data["next_agent_copy_paste_instructions"])


def test_operator_capsule_blocks_missing_matrix(tmp_path):
    root = copy_fixture_tree(tmp_path)
    (root / MATRIX).unlink()
    result = run_capsule(root)
    assert result.returncode == 2
    data = read_output(root)
    assert any("wave70_matrix_missing" in blocker for blocker in data["blockers"])
    assert data["public_actions_taken"] == []


def test_operator_capsule_blocks_failed_lane(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / MATRIX
    matrix = json.loads(path.read_text())
    matrix["lanes"][0]["passed"] = False
    path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n")
    result = run_capsule(root)
    assert result.returncode == 2
    data = read_output(root)
    assert "lane_not_passed: glm_gorilla_bootstrap_conveyor" in data["blockers"]


def test_operator_capsule_blocks_public_action_records(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / MATRIX
    matrix = json.loads(path.read_text())
    matrix["public_actions_taken"] = ["npm publish"]
    matrix["lanes"][2]["external_actions"] = ["discord webhook"]
    path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n")
    result = run_capsule(root)
    assert result.returncode == 2
    data = read_output(root)
    assert "wave70_matrix_records_public_actions_taken" in data["blockers"]
    assert "lane_records_external_actions: comms_hub" in data["blockers"]


def test_markdown_lists_instructions_commands_and_blockers(tmp_path):
    root = copy_fixture_tree(tmp_path)
    result = run_capsule(root)
    assert result.returncode == 0, result.stderr + result.stdout
    text = (root / "agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.md").read_text()
    assert "operator capsule (wave71)" in text
    assert "Next-agent copy/paste instructions" in text
    assert "Verification commands" in text
    assert "Public actions taken: `[]`" in text
