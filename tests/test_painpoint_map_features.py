import argparse
import importlib.util
import json
import pathlib

_SCRIPTS = pathlib.Path(__file__).parent.parent / "scripts"
_SPEC = importlib.util.spec_from_file_location("agentpress", _SCRIPTS / "agentpress.py")
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

painpoint_map = _MOD.painpoint_map
package_registry_doctor = _MOD.package_registry_doctor
handoff_pack = _MOD.handoff_pack


def _ns(**kwargs):
    base = {
        "root": ".",
        "out": "/tmp/agentpress-test.json",
        "base_url": "https://example.com/agentpress/",
        "mission_id": "mission-20260505-133622-52df70",
        "no_write": True,
        "json": True,
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


def test_painpoint_map_ranks_requested_agent_painpoints(capsys):
    rc = painpoint_map(_ns())
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "ok"
    assert data["ranked_painpoints"][0]["id"] == "first_run_onboarding_friction"
    assert len(data["ranked_painpoints"]) == 9
    assert set(data["feature_backlog"]) == {"P0", "P1", "P2"}
    assert "painpoint-map CLI" in data["shipped_this_sprint"][0]


def test_painpoint_map_write_creates_schema_versioned_json(tmp_path, capsys):
    out = tmp_path / "painpoint-map.json"
    rc = painpoint_map(_ns(out=str(out), no_write=False))
    capsys.readouterr()

    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["schema_version"] == "2026-05-05.agentpress-painpoint-map.v1"
    assert payload["safe_scope"]["package_publish"] is False


def test_package_registry_doctor_explains_stable_vs_rc(capsys):
    args = argparse.Namespace(
        error="npm ERR! 404 Not Found - @agent_press/agentpress",
        out="/tmp/pkg-doctor.json",
        base_url="https://example.com/agentpress/",
        no_write=True,
        json=True,
    )
    rc = package_registry_doctor(args)
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["schema_version"].endswith("package-registry-doctor.v2")
    assert data["version_channel"]["stable_latest"]["status"] == "not_asserted_without_registry_check"
    assert "registry_stable_unknown_without_network" in data["honest_labels"]


def test_handoff_pack_hashes_existing_evidence(tmp_path, capsys):
    artifact = tmp_path / "proof.json"
    artifact.write_text('{"status":"ok"}\n', encoding="utf-8")
    args = argparse.Namespace(
        from_agent="codex",
        to_agent="jake",
        task_id="mission-test",
        objective="Ship feature",
        constraints="no secrets",
        evidence=str(artifact),
        acceptance="tests pass",
        pending_actions="",
        out=str(tmp_path / "handoff.json"),
        base_url="https://example.com/agentpress/",
        no_write=True,
        json=True,
    )
    rc = handoff_pack(args)
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    row = data["evidence_manifest"][0]
    assert row["status"] == "present"
    assert len(row["sha256"]) == 64
    assert row["secret_scan"]["safe"] is True
    assert data["evidence_summary"]["present_count"] == 1
    assert "proof-capture" in data["proof_command"]


def test_handoff_pack_refuses_sensitive_evidence_path_without_reading(tmp_path, capsys):
    secret_dir = tmp_path / ".ssh"
    secret_dir.mkdir()
    secret_file = secret_dir / "id_rsa"
    secret_file.write_text("PRIVATE KEY should not be read\n", encoding="utf-8")
    args = argparse.Namespace(
        from_agent="codex",
        to_agent="jake",
        task_id="mission-test",
        objective="Ship feature",
        constraints="no secrets",
        evidence=str(secret_file),
        acceptance="tests pass",
        pending_actions="",
        out=str(tmp_path / "handoff.json"),
        base_url="https://example.com/agentpress/",
        no_write=True,
        json=True,
    )
    rc = handoff_pack(args)
    raw = capsys.readouterr().out
    data = json.loads(raw)

    assert rc == 0
    assert data["evidence_manifest"][0]["status"] == "refused_sensitive_path"
    assert data["evidence_summary"]["refused_sensitive_path_count"] == 1
    assert "PRIVATE KEY" not in raw
