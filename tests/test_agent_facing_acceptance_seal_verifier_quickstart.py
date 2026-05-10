from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_seal_verifier_quickstart.py"
spec = importlib.util.spec_from_file_location("wave78", SCRIPT)
wave78 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(wave78)


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _write(root: Path, rel: str, data: dict) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> dict[str, dict]:
    docs = {rel: _load(rel) for rel in wave78.REQUIRED_INPUTS}
    for rel, doc in docs.items():
        _write(tmp_path, rel, doc)
    package = {
        "scripts": {wave78.SCRIPT_NAME: "python3 scripts/agent_facing_acceptance_seal_verifier_quickstart.py . --include-pack-check --json"},
        "files": list(wave78.REQUIRED_OUTPUTS),
    }
    _write(tmp_path, "package.json", package)
    (tmp_path / wave78.SCRIPT_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / wave78.SCRIPT_PATH).write_text("# script\n", encoding="utf-8")
    (tmp_path / wave78.TEST_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / wave78.TEST_PATH).write_text("# test\n", encoding="utf-8")
    return docs


def test_valid_seal_verifier_quickstart(tmp_path: Path) -> None:
    _fixture(tmp_path)
    receipt = wave78.build_seal_verifier_quickstart(tmp_path)
    assert receipt["status"] == "ok"
    assert receipt["quickstart_id"].startswith("wave78-quickstart-")
    assert receipt["seal_id"].startswith("wave77-seal-")
    assert receipt["certificate_id"].startswith("wave73-certificate-")
    assert receipt["source_receipt_id"].startswith("wave72-readiness-")
    assert receipt["lane_count"] == 6
    assert receipt["command_count"] > 0
    assert receipt["transfer_step_count"] == 6
    assert receipt["rehearsed_step_count"] == 6
    assert receipt["rehearsed_lane_count"] == 6
    assert receipt["fresh_agent_verification_command_count"] >= 5
    assert len(receipt["artifact_inventory"]) == 8
    assert all(item["lane_count"] == 6 for item in receipt["artifact_inventory"])
    assert all(check["ok"] for check in receipt["cross_checks"].values())
    assert receipt["public_action_gate"] == "closed_until_jake_explicit_approval"
    assert receipt["public_actions_taken"] == []
    assert receipt["external_actions"] == []


def test_missing_wave77_blocks(tmp_path: Path) -> None:
    _fixture(tmp_path)
    (tmp_path / wave78.WAVE77).unlink()
    receipt = wave78.build_seal_verifier_quickstart(tmp_path)
    assert receipt["status"] == "blocked"
    assert any("missing_wave77_rehearsal_seal" in blocker and wave78.WAVE77 in blocker for blocker in receipt["blockers"])


def test_blocked_wave77_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave78.WAVE77])
    bad["status"] = "blocked"
    bad["blockers"] = ["synthetic"]
    _write(tmp_path, wave78.WAVE77, bad)
    receipt = wave78.build_seal_verifier_quickstart(tmp_path)
    assert receipt["status"] == "blocked"
    assert any("prior_artifact_status_not_ok" in blocker and wave78.WAVE77 in blocker for blocker in receipt["blockers"])
    assert any("prior_artifact_has_blockers" in blocker and wave78.WAVE77 in blocker for blocker in receipt["blockers"])


def test_seal_certificate_mismatch_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave78.WAVE77])
    bad["certificate_id"] = "wave73-certificate-mismatched"
    _write(tmp_path, wave78.WAVE77, bad)
    receipt = wave78.build_seal_verifier_quickstart(tmp_path)
    assert receipt["status"] == "blocked"
    assert "wave77_wave76_certificate_id_mismatch" in receipt["blockers"]
    assert "wave77_wave75_certificate_id_mismatch" in receipt["blockers"]


def test_missing_prior_artifact_blocks(tmp_path: Path) -> None:
    _fixture(tmp_path)
    (tmp_path / wave78.WAVE70).unlink()
    receipt = wave78.build_seal_verifier_quickstart(tmp_path)
    assert receipt["status"] == "blocked"
    assert any("missing_prior_artifact" in blocker and wave78.WAVE70 in blocker for blocker in receipt["blockers"])


def test_public_external_contamination_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad77 = copy.deepcopy(docs[wave78.WAVE77])
    bad76 = copy.deepcopy(docs[wave78.WAVE76])
    bad77["public_actions_taken"] = ["npm publish"]
    bad76["external_actions"] = ["outreach"]
    _write(tmp_path, wave78.WAVE77, bad77)
    _write(tmp_path, wave78.WAVE76, bad76)
    receipt = wave78.build_seal_verifier_quickstart(tmp_path)
    assert receipt["status"] == "blocked"
    assert any("public_actions_taken_contaminated" in blocker for blocker in receipt["blockers"])
    assert any("external_actions_contaminated" in blocker for blocker in receipt["blockers"])


def test_package_missing_output_blocks(tmp_path: Path) -> None:
    _fixture(tmp_path)
    package = json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))
    package["files"].remove(wave78.DEFAULT_MD)
    _write(tmp_path, "package.json", package)
    receipt = wave78.build_seal_verifier_quickstart(tmp_path)
    assert receipt["status"] == "blocked"
    assert f"package_json_files_missing: {wave78.DEFAULT_MD}" in receipt["blockers"]
