from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_recipient_rehearsal.py"
spec = importlib.util.spec_from_file_location("wave76", SCRIPT)
wave76 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(wave76)


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _write(root: Path, rel: str, data: dict) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> dict[str, dict]:
    docs = {rel: _load(rel) for rel in wave76.REQUIRED_INPUTS}
    for rel, doc in docs.items():
        _write(tmp_path, rel, doc)
    package = {
        "scripts": {wave76.SCRIPT_NAME: "python3 scripts/agent_facing_acceptance_recipient_rehearsal.py . --include-pack-check --json"},
        "files": list(wave76.REQUIRED_OUTPUTS),
    }
    _write(tmp_path, "package.json", package)
    (tmp_path / wave76.SCRIPT_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / wave76.SCRIPT_PATH).write_text("# script\n", encoding="utf-8")
    (tmp_path / wave76.TEST_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / wave76.TEST_PATH).write_text("# test\n", encoding="utf-8")
    return docs


def test_valid_recipient_rehearsal(tmp_path: Path) -> None:
    _fixture(tmp_path)
    receipt = wave76.build_recipient_rehearsal(tmp_path)
    assert receipt["status"] == "ok"
    assert receipt["certificate_id"].startswith("wave73-certificate-")
    assert receipt["source_receipt_id"].startswith("wave72-readiness-")
    assert receipt["lane_count"] == 6
    assert receipt["command_count"] > 0
    assert receipt["transfer_step_count"] == 6
    assert receipt["rehearsed_step_count"] == 6
    assert receipt["rehearsed_lane_count"] == 6
    assert receipt["public_action_gate"] == "closed_until_jake_explicit_approval"
    assert receipt["public_actions_taken"] == []
    assert receipt["external_actions"] == []


def test_missing_wave75_blocks(tmp_path: Path) -> None:
    _fixture(tmp_path)
    (tmp_path / wave76.WAVE75).unlink()
    receipt = wave76.build_recipient_rehearsal(tmp_path)
    assert receipt["status"] == "blocked"
    assert any("missing_wave75_transfer_checklist" in blocker and wave76.WAVE75 in blocker for blocker in receipt["blockers"])


def test_blocked_wave75_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave76.WAVE75])
    bad["status"] = "blocked"
    bad["blockers"] = ["synthetic"]
    _write(tmp_path, wave76.WAVE75, bad)
    receipt = wave76.build_recipient_rehearsal(tmp_path)
    assert receipt["status"] == "blocked"
    assert any("prior_artifact_status_not_ok" in blocker and wave76.WAVE75 in blocker for blocker in receipt["blockers"])
    assert any("prior_artifact_has_blockers" in blocker and wave76.WAVE75 in blocker for blocker in receipt["blockers"])


def test_lane_mismatch_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave76.WAVE75])
    bad["lane_count"] = 5
    _write(tmp_path, wave76.WAVE75, bad)
    receipt = wave76.build_recipient_rehearsal(tmp_path)
    assert receipt["status"] == "blocked"
    assert "wave75_lane_count_mismatch" in receipt["blockers"]


def test_missing_prior_artifact_blocks(tmp_path: Path) -> None:
    _fixture(tmp_path)
    (tmp_path / wave76.WAVE70).unlink()
    receipt = wave76.build_recipient_rehearsal(tmp_path)
    assert receipt["status"] == "blocked"
    assert any("missing_prior_artifact" in blocker and wave76.WAVE70 in blocker for blocker in receipt["blockers"])


def test_public_external_contamination_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad75 = copy.deepcopy(docs[wave76.WAVE75])
    bad74 = copy.deepcopy(docs[wave76.WAVE74])
    bad75["public_actions_taken"] = ["npm publish"]
    bad74["external_actions"] = ["outreach"]
    _write(tmp_path, wave76.WAVE75, bad75)
    _write(tmp_path, wave76.WAVE74, bad74)
    receipt = wave76.build_recipient_rehearsal(tmp_path)
    assert receipt["status"] == "blocked"
    assert any("public_actions_taken_contaminated" in blocker for blocker in receipt["blockers"])
    assert any("external_actions_contaminated" in blocker for blocker in receipt["blockers"])


def test_package_missing_output_blocks(tmp_path: Path) -> None:
    _fixture(tmp_path)
    package = json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))
    package["files"].remove(wave76.DEFAULT_MD)
    _write(tmp_path, "package.json", package)
    receipt = wave76.build_recipient_rehearsal(tmp_path)
    assert receipt["status"] == "blocked"
    assert f"package_json_files_missing: {wave76.DEFAULT_MD}" in receipt["blockers"]
