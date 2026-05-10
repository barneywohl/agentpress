from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_facing_acceptance_smoke_replay_receipt.py"
spec = importlib.util.spec_from_file_location("wave82", SCRIPT)
wave82 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(wave82)


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _write(root: Path, rel: str, data: dict) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> dict[str, dict]:
    docs = {rel: _load(rel) for rel in wave82.REQUIRED_INPUTS}
    for rel, doc in docs.items():
        _write(tmp_path, rel, doc)
    package = {
        "scripts": {wave82.SCRIPT_NAME: "python3 scripts/agent_facing_acceptance_smoke_replay_receipt.py . --include-pack-check --json"},
        "files": list(wave82.REQUIRED_OUTPUTS),
    }
    _write(tmp_path, "package.json", package)
    (tmp_path / wave82.SCRIPT_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / wave82.SCRIPT_PATH).write_text("# script\n", encoding="utf-8")
    (tmp_path / wave82.TEST_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / wave82.TEST_PATH).write_text("# test\n", encoding="utf-8")
    return docs


def test_valid_replay_receipt(tmp_path: Path) -> None:
    _fixture(tmp_path)
    receipt = wave82.build_receipt(tmp_path, run_inspections=False, run_replay=False)
    assert receipt["status"] == "ok"
    assert receipt["receipt_id"].startswith("wave82-smoke-replay-")
    assert receipt["selected_command"] == "npm run rc:agent-facing-acceptance-launchpad-card"
    assert all(check["ok"] for check in receipt["cross_checks"].values())
    assert all(row["local_safe"] and row["inspection_only"] and row["public_action_free"] and row["prior_flags_ok"] for row in receipt["packet_command_safety"])
    assert receipt["selected_command_replay"]["skipped"] is True
    assert receipt["public_action_gate"] == "closed_until_jake_explicit_approval"
    assert receipt["public_actions_taken"] == []
    assert receipt["external_actions"] == []


def test_missing_or_blocked_wave81_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    (tmp_path / wave82.WAVE81).unlink()
    missing = wave82.build_receipt(tmp_path, run_inspections=False, run_replay=False)
    assert missing["status"] == "blocked"
    assert any("missing_wave81_packet" in blocker for blocker in missing["blockers"])

    bad = copy.deepcopy(docs[wave82.WAVE81])
    bad["status"] = "blocked"
    bad["blockers"] = ["synthetic"]
    _write(tmp_path, wave82.WAVE81, bad)
    blocked = wave82.build_receipt(tmp_path, run_inspections=False, run_replay=False)
    assert blocked["status"] == "blocked"
    assert any("prior_status_not_ok" in blocker and wave82.WAVE81 in blocker for blocker in blocked["blockers"])
    assert any("prior_has_blockers" in blocker and wave82.WAVE81 in blocker for blocker in blocked["blockers"])


def test_selected_command_mismatch_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave82.WAVE81])
    bad["selected_command"] = "npm run rc:agent-facing-acceptance-rehearsal-seal"
    _write(tmp_path, wave82.WAVE81, bad)
    receipt = wave82.build_receipt(tmp_path, run_inspections=False, run_replay=False)
    assert receipt["status"] == "blocked"
    assert "wave81_selected_matches_paste_ready_first_command_failed" in receipt["blockers"]
    assert "wave81_selected_matches_wave80_selection_failed" in receipt["blockers"]
    assert "wave81_selected_matches_wave79_recommended_next_command_failed" in receipt["blockers"]


def test_missing_expected_output_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave82.WAVE81])
    bad["paste_ready_packet"]["expected_evidence_outputs"] = [wave82.WAVE81]
    _write(tmp_path, wave82.WAVE81, bad)
    receipt = wave82.build_receipt(tmp_path, run_inspections=False, run_replay=False)
    assert receipt["status"] == "blocked"
    assert "wave81_expected_outputs_present_failed" in receipt["blockers"]


def test_forbidden_packet_command_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave82.WAVE81])
    bad["packet_commands"][0]["command"] = "npm publish --dry-run"
    bad["packet_commands"][0]["local_safe"] = False
    _write(tmp_path, wave82.WAVE81, bad)
    receipt = wave82.build_receipt(tmp_path, run_inspections=False, run_replay=False)
    assert receipt["status"] == "blocked"
    assert "packet_command_safety_failed" in receipt["blockers"]
    assert any(row["forbidden_match"] for row in receipt["packet_command_safety"])


def test_public_external_contamination_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad81 = copy.deepcopy(docs[wave82.WAVE81])
    bad80 = copy.deepcopy(docs[wave82.WAVE80])
    bad81["public_actions_taken"] = ["git push"]
    bad80["external_actions"] = ["outreach"]
    _write(tmp_path, wave82.WAVE81, bad81)
    _write(tmp_path, wave82.WAVE80, bad80)
    receipt = wave82.build_receipt(tmp_path, run_inspections=False, run_replay=False)
    assert receipt["status"] == "blocked"
    assert any("public_actions_taken_contaminated" in blocker for blocker in receipt["blockers"])
    assert any("external_actions_contaminated" in blocker for blocker in receipt["blockers"])


def test_replay_failure_blocks(tmp_path: Path) -> None:
    docs = _fixture(tmp_path)
    bad = copy.deepcopy(docs[wave82.WAVE81])
    bad["selected_command"] = "python3 -c 'import sys; sys.exit(7)'"
    bad["paste_ready_packet"]["first_command"] = bad["selected_command"]
    bad80 = copy.deepcopy(docs[wave82.WAVE80])
    bad79 = copy.deepcopy(docs[wave82.WAVE79])
    bad80["first_command_selection"]["selected"] = bad["selected_command"]
    bad79["recommended_next_command"] = bad["selected_command"]
    _write(tmp_path, wave82.WAVE81, bad)
    _write(tmp_path, wave82.WAVE80, bad80)
    _write(tmp_path, wave82.WAVE79, bad79)
    receipt = wave82.build_receipt(tmp_path, run_inspections=False, run_replay=True)
    assert receipt["status"] == "blocked"
    assert "selected_command_replay_failed" in receipt["blockers"]
    assert receipt["selected_command_replay"]["returncode"] == 7
