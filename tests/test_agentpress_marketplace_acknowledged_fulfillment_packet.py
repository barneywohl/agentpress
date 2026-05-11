from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agentpress_marketplace_acknowledged_fulfillment_packet.py"
spec = importlib.util.spec_from_file_location("wave105", SCRIPT)
wave105 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(wave105)


def test_packet_builds_ok_from_wave104_acknowledgement() -> None:
    packet = wave105.build_packet(ROOT)
    assert packet["status"] == "ok"
    assert packet["public_push_publish_deploy"] is False
    assert packet["external_actions"] == []
    assert packet["payment_actions_taken"] == []
    assert packet["secret_material_included"] is False
    assert packet["jake_explicit_approval_required_for_public_actions"] is True


def test_trust_checks_are_all_true_and_agent_facing() -> None:
    packet = wave105.build_packet(ROOT)
    checks = packet["fulfillment_packet"]["trust_checks"]
    assert checks
    assert all(row["ok"] is True for row in checks)
    assert "trust-checked local marketplace fulfillment packet" in packet["agent_facing_value"]
    assert packet["fulfillment_packet"]["fulfillment_mode"] == "local_only_trust_checked"


def test_handoff_artifacts_are_local_relative_paths() -> None:
    packet = wave105.build_packet(ROOT)
    for artifact in packet["fulfillment_packet"]["local_artifacts"]:
        assert wave105.local_rel(artifact)
    for artifact in packet["handoff_ready_artifacts"]:
        assert wave105.local_rel(artifact)


def test_package_registration_is_present() -> None:
    packet = wave105.build_packet(ROOT)
    package = packet["package"]
    assert package["script"].startswith("python3 scripts/agentpress_marketplace_acknowledged_fulfillment_packet.py")
    missing = [row for row in package["required"] if not row["listed_in_package_files"]]
    assert missing == []


def test_unsafe_acknowledgement_is_blocked() -> None:
    source = {
        "status": "ok",
        "public_push_publish_deploy": False,
        "jake_explicit_approval_required_for_public_actions": True,
        "external_actions": [],
        "payment_actions_taken": [],
        "sample_operator_acknowledgement": {
            "operator_agent_id": "local-recipient-agent",
            "operator_acknowledged_first_command": True,
            "first_command_exit_code": 0,
            "criteria_checked": ["checked"],
            "generated_local_artifacts": ["https://example.invalid/not-local.json"],
        },
    }
    ack, blockers = wave105.acknowledgement_ok(source)
    assert ack["operator_agent_id"] == "local-recipient-agent"
    assert any(item.startswith("ack_artifact_not_local") for item in blockers)
