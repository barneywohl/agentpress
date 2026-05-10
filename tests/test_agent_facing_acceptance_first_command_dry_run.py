from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_first_command_dry_run.py"
spec = importlib.util.spec_from_file_location("wave80", SCRIPT)
wave80 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(wave80)


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _write(root: Path, rel: str, data: dict) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> dict[str, dict]:
    docs = {rel: _load(rel) for rel in wave80.REQUIRED_INPUTS}
    for rel, doc in docs.items():
        _write(tmp_path, rel, doc)
    package = {
        "scripts": {wave80.SCRIPT_NAME: "python3 scripts/agent_facing_acceptance_first_command_dry_run.py . --include-pack-check --json"},
        "files": list(wave80.REQUIRED_OUTPUTS),
    }
    _write(tmp_path, "package.json", package)
    (tmp_path / wave80.SCRIPT_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / wave80.SCRIPT_PATH).write_text("# script\n", encoding="utf-8")
    (tmp_path / wave80.TEST_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / wave80.TEST_PATH).write_text("# test\n", encoding="utf-8")
    return docs


def test_valid_first_command_dry_run(tmp_path: Path) -> None:
    _fixture(tmp_path)
    receipt = wave80.build_first_command_dry_run(tmp_path, run_inspections=False)
    assert receipt["status"] == "ok"
    assert receipt["dry_run_id"].startswith("wave80-first-command-")
    assert receipt["launchpad_card_id"].startswith("wave79-card-")
    assert receipt["quickstart_id"].startswith("wave78-quickstart-")
    assert receipt["seal_id"].startswith("wave77-seal-")
    assert receipt["certificate_id"].startswith("wave73-certificate-")
    assert receipt["source_receipt_id"].startswith("wave72-readiness-")
    assert receipt["lane_count"] == 6
    assert receipt["rehearsed_lane_count"] == 6
    assert receipt["artifact_inventory_count"] >= 8
    assert receipt["ordered_verification_command_count"] >= 5
    assert receipt["recommended_next_command"]
    assert len(receipt["rehearsed_commands"]) >= 10
    assert all(row["local_safe"] and row["inspection_only"] and row["public_action_free"] for row in receipt["rehearsed_commands"])
    assert all(check["ok"] for check in receipt["cross_checks"].values())
    assert receipt["public_action_gate"] == "closed_until_jake_explicit_approval"
    assert receipt["public_actions_taken"] == []
    assert receipt["external_actions"] == []


def test_missing_wave79_blocks(tmp_path: Path) -> None:
    _fixture(tmp_path)
    (tmp_path / wave80.WAVE79).unlink()
    receipt = wave80.build_first_command_dry_run(tmp_path, run_inspections=False)
    assert receipt["status"] == "blocked"
    assert any("missing_wave79_launchpad_card" in blocker for blocker in receipt["blockers"])


def test_blocked_wave79_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave80.WAVE79])
    bad["status"] = "blocked"
    bad["blockers"] = ["synthetic"]
    _write(tmp_path, wave80.WAVE79, bad)
    receipt = wave80.build_first_command_dry_run(tmp_path, run_inspections=False)
    assert receipt["status"] == "blocked"
    assert any("prior_artifact_status_not_ok" in blocker and wave80.WAVE79 in blocker for blocker in receipt["blockers"])
    assert any("prior_artifact_has_blockers" in blocker and wave80.WAVE79 in blocker for blocker in receipt["blockers"])


def test_id_mismatch_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave80.WAVE79])
    bad["quickstart_id"] = "wave78-quickstart-mismatch"
    _write(tmp_path, wave80.WAVE79, bad)
    receipt = wave80.build_first_command_dry_run(tmp_path, run_inspections=False)
    assert receipt["status"] == "blocked"
    assert "wave79_matches_wave78_quickstart_id_mismatch" in receipt["blockers"]


def test_command_count_regression_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave80.WAVE79])
    bad["ordered_verification_command_count"] = 4
    bad["alternative_commands"] = bad["alternative_commands"][:4]
    _write(tmp_path, wave80.WAVE79, bad)
    receipt = wave80.build_first_command_dry_run(tmp_path, run_inspections=False)
    assert receipt["status"] == "blocked"
    assert "wave79_ordered_command_count_regression" in receipt["blockers"]
    assert "wave79_fewer_than_5_alternative_commands" in receipt["blockers"]


def test_missing_prior_artifact_blocks(tmp_path: Path) -> None:
    _fixture(tmp_path)
    (tmp_path / wave80.WAVE70).unlink()
    receipt = wave80.build_first_command_dry_run(tmp_path, run_inspections=False)
    assert receipt["status"] == "blocked"
    assert any("missing_prior_artifact" in blocker and wave80.WAVE70 in blocker for blocker in receipt["blockers"])


def test_public_external_and_forbidden_command_contamination_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad79 = copy.deepcopy(docs[wave80.WAVE79])
    bad78 = copy.deepcopy(docs[wave80.WAVE78])
    bad79["public_actions_taken"] = ["npm publish"]
    bad79["alternative_commands"][0] = "npm publish --dry-run"
    bad78["external_actions"] = ["outreach"]
    _write(tmp_path, wave80.WAVE79, bad79)
    _write(tmp_path, wave80.WAVE78, bad78)
    receipt = wave80.build_first_command_dry_run(tmp_path, run_inspections=False)
    assert receipt["status"] == "blocked"
    assert any("public_actions_taken_contaminated" in blocker for blocker in receipt["blockers"])
    assert any("external_actions_contaminated" in blocker for blocker in receipt["blockers"])
    assert "forbidden_command_text_detected" in receipt["blockers"]
    assert any(row["forbidden_match"] for row in receipt["rehearsed_commands"])
