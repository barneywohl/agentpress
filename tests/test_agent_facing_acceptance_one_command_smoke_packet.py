from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_one_command_smoke_packet.py"
spec = importlib.util.spec_from_file_location("wave81", SCRIPT)
wave81 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(wave81)


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _write(root: Path, rel: str, data: dict) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> dict[str, dict]:
    docs = {rel: _load(rel) for rel in wave81.REQUIRED_INPUTS}
    for rel, doc in docs.items():
        _write(tmp_path, rel, doc)
    package = {
        "scripts": {wave81.SCRIPT_NAME: "python3 scripts/agent_facing_acceptance_one_command_smoke_packet.py . --include-pack-check --json"},
        "files": list(wave81.REQUIRED_OUTPUTS),
    }
    _write(tmp_path, "package.json", package)
    (tmp_path / wave81.SCRIPT_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / wave81.SCRIPT_PATH).write_text("# script\n", encoding="utf-8")
    (tmp_path / wave81.TEST_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / wave81.TEST_PATH).write_text("# test\n", encoding="utf-8")
    return docs


def test_valid_smoke_packet(tmp_path: Path) -> None:
    _fixture(tmp_path)
    packet = wave81.build_smoke_packet(tmp_path, run_inspections=False)
    assert packet["status"] == "ok"
    assert packet["packet_id"].startswith("wave81-smoke-packet-")
    assert packet["selected_command"] == "npm run rc:agent-facing-acceptance-launchpad-card"
    assert packet["paste_ready_packet"]["first_command"] == packet["selected_command"]
    assert wave81.DEFAULT_OUT in packet["paste_ready_packet"]["expected_evidence_outputs"]
    assert wave81.DEFAULT_MD in packet["paste_ready_packet"]["expected_evidence_outputs"]
    assert all(row["local_safe"] and row["inspection_only"] and row["public_action_free"] for row in packet["packet_commands"])
    assert all(check["ok"] for check in packet["cross_checks"].values())
    assert packet["public_action_gate"] == "closed_until_jake_explicit_approval"
    assert packet["public_actions_taken"] == []
    assert packet["external_actions"] == []


def test_missing_or_blocked_wave80_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    (tmp_path / wave81.WAVE80).unlink()
    missing = wave81.build_smoke_packet(tmp_path, run_inspections=False)
    assert missing["status"] == "blocked"
    assert any("missing_wave80_first_command" in blocker for blocker in missing["blockers"])

    bad = copy.deepcopy(docs[wave81.WAVE80])
    bad["status"] = "blocked"
    bad["blockers"] = ["synthetic"]
    _write(tmp_path, wave81.WAVE80, bad)
    blocked = wave81.build_smoke_packet(tmp_path, run_inspections=False)
    assert blocked["status"] == "blocked"
    assert any("prior_status_not_ok" in blocker and wave81.WAVE80 in blocker for blocker in blocked["blockers"])
    assert any("prior_has_blockers" in blocker and wave81.WAVE80 in blocker for blocker in blocked["blockers"])


def test_selected_command_mismatch_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave81.WAVE80])
    bad["first_command_selection"]["selected"] = "npm run rc:agent-facing-acceptance-rehearsal-seal"
    _write(tmp_path, wave81.WAVE80, bad)
    packet = wave81.build_smoke_packet(tmp_path, run_inspections=False)
    assert packet["status"] == "blocked"
    assert "selected_command_mismatch_wave79_recommended_next_command" in packet["blockers"]
    assert "selected_matches_wave79_recommended_next_command_failed" in packet["blockers"]


def test_command_count_regression_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave81.WAVE80])
    bad["rehearsed_command_count"] = 4
    bad["ordered_verification_command_count"] = 4
    _write(tmp_path, wave81.WAVE80, bad)
    packet = wave81.build_smoke_packet(tmp_path, run_inspections=False)
    assert packet["status"] == "blocked"
    assert "wave80_rehearsed_command_count_regression" in packet["blockers"]
    assert "command_count_not_regressed_failed" in packet["blockers"]


def test_missing_prior_artifact_blocks(tmp_path: Path) -> None:
    _fixture(tmp_path)
    (tmp_path / wave81.WAVE78).unlink()
    packet = wave81.build_smoke_packet(tmp_path, run_inspections=False)
    assert packet["status"] == "blocked"
    assert any("missing_prior_artifact" in blocker and wave81.WAVE78 in blocker for blocker in packet["blockers"])


def test_public_external_and_forbidden_command_contamination_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad80 = copy.deepcopy(docs[wave81.WAVE80])
    bad79 = copy.deepcopy(docs[wave81.WAVE79])
    bad80["public_actions_taken"] = ["git push"]
    bad80["first_command_selection"]["selected"] = "npm publish --dry-run"
    bad79["external_actions"] = ["outreach"]
    bad79["recommended_next_command"] = "npm publish --dry-run"
    _write(tmp_path, wave81.WAVE80, bad80)
    _write(tmp_path, wave81.WAVE79, bad79)
    packet = wave81.build_smoke_packet(tmp_path, run_inspections=False)
    assert packet["status"] == "blocked"
    assert any("public_actions_taken_contaminated" in blocker for blocker in packet["blockers"])
    assert any("external_actions_contaminated" in blocker for blocker in packet["blockers"])
    assert "forbidden_command_text_detected" in packet["blockers"]
    assert any(row["forbidden_match"] for row in packet["packet_commands"])
