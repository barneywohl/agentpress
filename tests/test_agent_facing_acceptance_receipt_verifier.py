import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_receipt_verifier.py"
SOURCE = "agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.json"
OUT = "agentpress/evidence/agent-facing-acceptance-receipt-verifier-wave73.json"


def copy_fixture_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "agentpress/evidence").mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    shutil.copy(SCRIPT, root / "scripts/agent_facing_acceptance_receipt_verifier.py")
    shutil.copy(Path(__file__), root / "tests/test_agent_facing_acceptance_receipt_verifier.py")
    shutil.copy(ROOT / SOURCE, root / SOURCE)
    guardrail = ROOT / "agentpress/evidence/rc-public-action-guardrail-audit-wave52.json"
    if guardrail.exists():
        shutil.copy(guardrail, root / "agentpress/evidence/rc-public-action-guardrail-audit-wave52.json")
    package = json.loads((ROOT / "package.json").read_text())
    package["scripts"] = {
        "rc:agent-facing-acceptance-receipt-verifier": "python3 scripts/agent_facing_acceptance_receipt_verifier.py . --out agentpress/evidence/agent-facing-acceptance-receipt-verifier-wave73.json --markdown-out agentpress/evidence/agent-facing-acceptance-receipt-verifier-wave73.md --json"
    }
    package["files"] = list(set(package.get("files", [])) | {
        "scripts/agent_facing_acceptance_receipt_verifier.py",
        "tests/test_agent_facing_acceptance_receipt_verifier.py",
        "agentpress/evidence/agent-facing-acceptance-receipt-verifier-wave73.json",
        "agentpress/evidence/agent-facing-acceptance-receipt-verifier-wave73.md",
    })
    (root / "package.json").write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    return root


def run_verifier(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(root / "scripts/agent_facing_acceptance_receipt_verifier.py"), str(root), "--json", *extra],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def read_output(root: Path) -> dict:
    return json.loads((root / OUT).read_text())


def test_receipt_verifier_valid_wave72_emits_operator_certificate(tmp_path):
    root = copy_fixture_tree(tmp_path)
    result = run_verifier(root)
    assert result.returncode == 0, result.stderr + result.stdout
    data = read_output(root)
    assert data["status"] == "ok"
    assert data["public_actions_taken"] == []
    assert data["external_actions"] == []
    cert = data["operator_certificate"]
    assert cert["certificate_id"].startswith("wave73-certificate-")
    assert cert["source_receipt_id"].startswith("wave72-readiness-")
    assert cert["lane_count"] == 6
    assert cert["command_count"] >= 5
    assert cert["public_action_gate"] == "closed_until_jake_explicit_approval"


def test_receipt_verifier_blocks_missing_receipt(tmp_path):
    root = copy_fixture_tree(tmp_path)
    source = json.loads((root / SOURCE).read_text())
    source.pop("readiness_receipt")
    (root / SOURCE).write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_verifier(root)
    assert result.returncode == 2
    data = read_output(root)
    assert "wave72_missing_readiness_receipt" in data["blockers"]


def test_receipt_verifier_blocks_partial_lane_understanding(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / SOURCE
    source = json.loads(path.read_text())
    source["replayed_lane_summaries"] = source["replayed_lane_summaries"][:-1]
    source["readiness_receipt"]["all_required_lanes_understood"] = False
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_verifier(root)
    assert result.returncode == 2
    data = read_output(root)
    assert "wave72_receipt_not_all_required_lanes_understood" in data["blockers"]
    assert any("wave72_missing_required_lanes" in blocker for blocker in data["blockers"])


def test_receipt_verifier_blocks_blocked_source(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / SOURCE
    source = json.loads(path.read_text())
    source["status"] = "blocked"
    source["blockers"] = ["blocked upstream"]
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_verifier(root)
    assert result.returncode == 2
    data = read_output(root)
    assert "wave72_source_status_not_ok: 'blocked'" in data["blockers"]
    assert "wave72_source_has_blockers" in data["blockers"]


def test_receipt_verifier_blocks_public_external_and_forbidden_command_contamination(tmp_path):
    root = copy_fixture_tree(tmp_path)
    path = root / SOURCE
    source = json.loads(path.read_text())
    source["public_actions_taken"] = ["npm publish"]
    source["external_actions"] = ["discord webhook"]
    source["readiness_receipt"]["exact_local_commands"].append("git push origin main")
    path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    result = run_verifier(root)
    assert result.returncode == 2
    data = read_output(root)
    assert "wave72_source_records_public_actions_taken" in data["blockers"]
    assert "wave72_source_records_external_actions" in data["blockers"]
    assert any("wave72_receipt_contains_forbidden_fragments" in blocker for blocker in data["blockers"])


def test_markdown_lists_certificate_commands_and_blockers(tmp_path):
    root = copy_fixture_tree(tmp_path)
    result = run_verifier(root)
    assert result.returncode == 0, result.stderr + result.stdout
    text = (root / "agentpress/evidence/agent-facing-acceptance-receipt-verifier-wave73.md").read_text()
    assert "receipt verifier (wave73)" in text
    assert "Certificate" in text
    assert "Verified command fragments" in text
    assert "Public actions taken: `[]`" in text
