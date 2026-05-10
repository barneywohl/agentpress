from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_launchpad_card.py"
spec = importlib.util.spec_from_file_location("wave79", SCRIPT)
wave79 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(wave79)


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _write(root: Path, rel: str, data: dict) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> dict[str, dict]:
    docs = {rel: _load(rel) for rel in wave79.REQUIRED_INPUTS}
    for rel, doc in docs.items():
        _write(tmp_path, rel, doc)
    package = {
        "scripts": {wave79.SCRIPT_NAME: "python3 scripts/agent_facing_acceptance_launchpad_card.py . --include-pack-check --json"},
        "files": list(wave79.REQUIRED_OUTPUTS),
    }
    _write(tmp_path, "package.json", package)
    (tmp_path / wave79.SCRIPT_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / wave79.SCRIPT_PATH).write_text("# script\n", encoding="utf-8")
    (tmp_path / wave79.TEST_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / wave79.TEST_PATH).write_text("# test\n", encoding="utf-8")
    return docs


def test_valid_launchpad_card(tmp_path: Path) -> None:
    _fixture(tmp_path)
    receipt = wave79.build_launchpad_card(tmp_path)
    assert receipt["status"] == "ok"
    assert receipt["launchpad_card_id"].startswith("wave79-card-")
    assert receipt["recommended_next_command"] == f"npm run {wave79.SCRIPT_NAME}"
    assert receipt["quickstart_id"].startswith("wave78-quickstart-")
    assert receipt["seal_id"].startswith("wave77-seal-")
    assert receipt["certificate_id"].startswith("wave73-certificate-")
    assert receipt["source_receipt_id"].startswith("wave72-readiness-")
    assert receipt["lane_count"] == 6
    assert receipt["rehearsed_lane_count"] == 6
    assert receipt["artifact_inventory_count"] >= 8
    assert receipt["ordered_verification_command_count"] >= 5
    assert len(receipt["alternative_commands"]) >= 5
    assert all(check["ok"] for check in receipt["cross_checks"].values())
    assert receipt["public_action_gate"] == "closed_until_jake_explicit_approval"
    assert receipt["public_actions_taken"] == []
    assert receipt["external_actions"] == []


def test_missing_wave78_blocks(tmp_path: Path) -> None:
    _fixture(tmp_path)
    (tmp_path / wave79.WAVE78).unlink()
    receipt = wave79.build_launchpad_card(tmp_path)
    assert receipt["status"] == "blocked"
    assert any("missing_wave78_quickstart" in blocker for blocker in receipt["blockers"])


def test_blocked_wave78_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave79.WAVE78])
    bad["status"] = "blocked"
    bad["blockers"] = ["synthetic"]
    _write(tmp_path, wave79.WAVE78, bad)
    receipt = wave79.build_launchpad_card(tmp_path)
    assert receipt["status"] == "blocked"
    assert any("prior_artifact_status_not_ok" in blocker and wave79.WAVE78 in blocker for blocker in receipt["blockers"])
    assert any("prior_artifact_has_blockers" in blocker and wave79.WAVE78 in blocker for blocker in receipt["blockers"])


def test_quickstart_seal_mismatch_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave79.WAVE78])
    bad["seal_id"] = "wave77-seal-mismatch"
    _write(tmp_path, wave79.WAVE78, bad)
    receipt = wave79.build_launchpad_card(tmp_path)
    assert receipt["status"] == "blocked"
    assert "quickstart_seal_seal_id_mismatch" in receipt["blockers"]


def test_command_count_regression_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave79.WAVE78])
    bad["fresh_agent_verification_commands"] = bad["fresh_agent_verification_commands"][:4]
    _write(tmp_path, wave79.WAVE78, bad)
    receipt = wave79.build_launchpad_card(tmp_path)
    assert receipt["status"] == "blocked"
    assert "wave78_fewer_than_5_ordered_verification_commands" in receipt["blockers"]


def test_missing_prior_artifact_blocks(tmp_path: Path) -> None:
    _fixture(tmp_path)
    (tmp_path / wave79.WAVE70).unlink()
    receipt = wave79.build_launchpad_card(tmp_path)
    assert receipt["status"] == "blocked"
    assert any("missing_prior_artifact" in blocker and wave79.WAVE70 in blocker for blocker in receipt["blockers"])


def test_public_external_contamination_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad78 = copy.deepcopy(docs[wave79.WAVE78])
    bad77 = copy.deepcopy(docs[wave79.WAVE77])
    bad78["public_actions_taken"] = ["npm publish"]
    bad77["external_actions"] = ["outreach"]
    _write(tmp_path, wave79.WAVE78, bad78)
    _write(tmp_path, wave79.WAVE77, bad77)
    receipt = wave79.build_launchpad_card(tmp_path)
    assert receipt["status"] == "blocked"
    assert any("public_actions_taken_contaminated" in blocker for blocker in receipt["blockers"])
    assert any("external_actions_contaminated" in blocker for blocker in receipt["blockers"])
