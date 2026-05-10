from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_certificate_replay_drill.py"
spec = importlib.util.spec_from_file_location("wave74", SCRIPT)
wave74 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(wave74)


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _write(root: Path, rel: str, data: dict) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[dict, dict]:
    cert = _load(wave74.CERTIFICATE)
    source = _load(wave74.SOURCE)
    _write(tmp_path, wave74.CERTIFICATE, cert)
    _write(tmp_path, wave74.SOURCE, source)
    package = {
        "scripts": {wave74.SCRIPT_NAME: "python3 scripts/agent_facing_acceptance_certificate_replay_drill.py . --include-pack-check --json"},
        "files": list(wave74.REQUIRED_OUTPUTS),
    }
    _write(tmp_path, "package.json", package)
    (tmp_path / wave74.SCRIPT_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / wave74.SCRIPT_PATH).write_text("# script\n", encoding="utf-8")
    (tmp_path / wave74.TEST_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / wave74.TEST_PATH).write_text("# test\n", encoding="utf-8")
    return cert, source


def test_valid_replay(tmp_path: Path) -> None:
    _fixture(tmp_path)
    receipt = wave74.replay(tmp_path)
    assert receipt["status"] == "ok"
    assert receipt["certificate_id"].startswith("wave73-certificate-")
    assert receipt["source_receipt_id"]
    assert receipt["lane_count"] == 6
    assert receipt["command_count"] > 0
    assert receipt["replayed_assertion_count"] >= 10
    assert receipt["public_action_gate"] == "closed_until_jake_explicit_approval"
    assert receipt["public_actions_taken"] == []
    assert receipt["external_actions"] == []


def test_missing_certificate_blocks(tmp_path: Path) -> None:
    _fixture(tmp_path)
    (tmp_path / wave74.CERTIFICATE).unlink()
    receipt = wave74.replay(tmp_path)
    assert receipt["status"] == "blocked"
    assert any("missing_certificate" in blocker for blocker in receipt["blockers"])


def test_lane_mismatch_blocks(tmp_path: Path) -> None:
    cert, _ = _fixture(tmp_path)
    bad = copy.deepcopy(cert)
    bad["operator_certificate"]["lane_count"] = 5
    _write(tmp_path, wave74.CERTIFICATE, bad)
    receipt = wave74.replay(tmp_path)
    assert receipt["status"] == "blocked"
    assert "lane_count_mismatch" in receipt["blockers"]


def test_blocked_source_blocks(tmp_path: Path) -> None:
    _, source = _fixture(tmp_path)
    bad = copy.deepcopy(source)
    bad["status"] = "blocked"
    bad["blockers"] = ["synthetic"]
    _write(tmp_path, wave74.SOURCE, bad)
    receipt = wave74.replay(tmp_path)
    assert receipt["status"] == "blocked"
    assert any("source_status_not_ok" in blocker for blocker in receipt["blockers"])
    assert "source_has_blockers" in receipt["blockers"]


def test_missing_source_receipt_blocks(tmp_path: Path) -> None:
    _, source = _fixture(tmp_path)
    bad = copy.deepcopy(source)
    bad.pop("readiness_receipt", None)
    _write(tmp_path, wave74.SOURCE, bad)
    receipt = wave74.replay(tmp_path)
    assert receipt["status"] == "blocked"
    assert "missing_source_receipt_id" in receipt["blockers"]
    assert "source_exact_local_commands_missing" in receipt["blockers"]


def test_public_external_contamination_blocks(tmp_path: Path) -> None:
    cert, source = _fixture(tmp_path)
    bad_cert = copy.deepcopy(cert)
    bad_source = copy.deepcopy(source)
    bad_cert["public_actions_taken"] = ["npm publish"]
    bad_source["external_actions"] = ["outreach"]
    _write(tmp_path, wave74.CERTIFICATE, bad_cert)
    _write(tmp_path, wave74.SOURCE, bad_source)
    receipt = wave74.replay(tmp_path)
    assert receipt["status"] == "blocked"
    assert "certificate_public_actions_taken_contaminated" in receipt["blockers"]
    assert "source_external_actions_contaminated" in receipt["blockers"]


def test_command_count_zero_blocks(tmp_path: Path) -> None:
    cert, _ = _fixture(tmp_path)
    bad = copy.deepcopy(cert)
    bad["operator_certificate"]["command_count"] = 0
    _write(tmp_path, wave74.CERTIFICATE, bad)
    receipt = wave74.replay(tmp_path)
    assert receipt["status"] == "blocked"
    assert "command_count_zero_or_invalid" in receipt["blockers"]
