import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_handoff_drill.py"
CAPSULE = "agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.json"
OUT = "agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.json"


def copy_fixture_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "agentpress/evidence").mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    shutil.copy(SCRIPT, root / "scripts/agent_facing_acceptance_handoff_drill.py")
    shutil.copy(Path(__file__), root / "tests/test_agent_facing_acceptance_handoff_drill.py")
    shutil.copy(ROOT / CAPSULE, root / CAPSULE)
    package = json.loads((ROOT / "package.json").read_text())
    package["scripts"] = {
        "rc:agent-facing-acceptance-handoff-drill": "python3 scripts/agent_facing_acceptance_handoff_drill.py . --out agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.json --markdown-out agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.md --json"
    }
    package["files"] = list(set(package.get("files", [])) | {
        "scripts/agent_facing_acceptance_handoff_drill.py",
        "tests/test_agent_facing_acceptance_handoff_drill.py",
        "agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.json",
        "agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.md",
    })
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    return root


def run_drill(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(root / "scripts/agent_facing_acceptance_handoff_drill.py"), str(root), "--json", *extra],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def read_output(root: Path) -> dict:
    return json.loads((root / OUT).read_text())


def test_handoff_drill_valid_capsule_emits_readiness_receipt_without_public_actions(tmp_path):
    root = copy_fixture_tree(tmp_path)
    result = run_drill(root)
    assert result.returncode == 0, result.stderr + result.stdout
    data = read_output(root)
    assert data["status"] == "ok"
    assert data["public_actions_taken"] == []
    assert data["external_actions"] == []
    assert len(data["replayed_lane_summaries"]) == 6
    receipt = data["readiness_receipt"]
    assert receipt["receipt_id"].startswith("wave72-readiness-")
    assert receipt["all_required_lanes_understood"] is True
    assert receipt["public_action_gate_state"] == "closed_until_jake_explicit_approval"
    assert any("rc:agent-facing-acceptance-handoff-drill" in command for command in receipt["exact_local_commands"])


def test_handoff_drill_blocks_missing_capsule(tmp_path):
    root = copy_fixture_tree(tmp_path)
    (root / CAPSULE).unlink()
    result = run_drill(root)
    assert result.returncode == 2
    data = read_output(root)
    assert any("wave71_capsule_missing" in blocker for blocker in data["blockers"])
    assert data["public_actions_taken"] == []


def test_handoff_drill_blocks_blocked_capsule(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / CAPSULE
    capsule = json.loads(path.read_text())
    capsule["status"] = "blocked"
    capsule["blockers"] = ["operator capsule blocked"]
    path.write_text(json.dumps(capsule, indent=2, sort_keys=True) + "\n")
    result = run_drill(root)
    assert result.returncode == 2
    data = read_output(root)
    assert "wave71_capsule_status_not_ok: 'blocked'" in data["blockers"]
    assert "wave71_capsule_has_blockers" in data["blockers"]


def test_handoff_drill_blocks_missing_or_partial_lane_summary(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / CAPSULE
    capsule = json.loads(path.read_text())
    capsule["lane_summaries"] = capsule["lane_summaries"][:-1]
    capsule["lane_summaries"][0]["required_sources"] = []
    path.write_text(json.dumps(capsule, indent=2, sort_keys=True) + "\n")
    result = run_drill(root)
    assert result.returncode == 2
    data = read_output(root)
    assert "missing_required_lane_summary: acceptance_harness" in data["blockers"]
    assert "lane_summary_missing_required_sources: glm_gorilla_bootstrap_conveyor" in data["blockers"]


def test_handoff_drill_blocks_public_and_external_action_contamination(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / CAPSULE
    capsule = json.loads(path.read_text())
    capsule["public_actions_taken"] = ["npm publish"]
    capsule["external_actions"] = ["discord webhook"]
    capsule["exact_local_verification_commands"].append("git push origin main")
    path.write_text(json.dumps(capsule, indent=2, sort_keys=True) + "\n")
    result = run_drill(root)
    assert result.returncode == 2
    data = read_output(root)
    assert "wave71_capsule_records_public_actions_taken" in data["blockers"]
    assert "wave71_capsule_records_external_actions" in data["blockers"]
    assert any("wave71_capsule_contains_forbidden_fragments" in blocker for blocker in data["blockers"])


def test_markdown_lists_readiness_receipt_commands_and_blockers(tmp_path):
    root = copy_fixture_tree(tmp_path)
    result = run_drill(root)
    assert result.returncode == 0, result.stderr + result.stdout
    text = (root / "agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.md").read_text()
    assert "handoff drill (wave72)" in text
    assert "Readiness receipt" in text
    assert "Fresh-agent lane understanding" in text
    assert "Public actions taken: `[]`" in text
