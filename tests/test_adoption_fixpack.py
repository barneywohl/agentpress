"""Tests for adoption-fixpack command."""
import argparse
import importlib.util
import json
import pathlib

_SCRIPTS = pathlib.Path(__file__).parent.parent / "scripts"
_SPEC = importlib.util.spec_from_file_location("agentpress", _SCRIPTS / "agentpress.py")
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

adoption_fixpack = _MOD.adoption_fixpack


def _ns(tmp_path, **kwargs):
    base = {
        "root": str(tmp_path),
        "out": str(tmp_path / "fixpack"),
        "adoption_status": "agentpress/adoption/adoption-status.json",
        "docs_check": "agentpress/evidence/docs-command-check.json",
        "lint_result": "agentpress/evidence/agentpress-lint.json",
        "base_url": "https://example.com/agentpress/",
        "no_write": True,
        "json": True,
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


def _seed_inputs(root):
    (root / "agentpress/adoption").mkdir(parents=True)
    (root / "agentpress/evidence").mkdir(parents=True)
    (root / "agentpress/adoption/adoption-status.json").write_text(json.dumps({
        "status": "needs_attention",
        "metrics": {"third_party_receipts": 0, "install_lanes_live": 1},
    }))
    (root / "agentpress/evidence/docs-command-check.json").write_text(json.dumps({
        "status": "ok",
        "checks": [],
    }))
    (root / "agentpress/evidence/agentpress-lint.json").write_text(json.dumps({
        "status": "ok",
        "findings": [],
    }))


def test_fixpack_flags_no_external_receipts(capsys, tmp_path):
    _seed_inputs(tmp_path)
    rc = adoption_fixpack(_ns(tmp_path))
    data = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert data["status"] == "needs_external_proof"
    assert any(b["id"] == "no_third_party_receipts" for b in data["blockers"])


def test_fixpack_contains_copy_paste_proof_commands(capsys, tmp_path):
    _seed_inputs(tmp_path)
    adoption_fixpack(_ns(tmp_path))
    data = json.loads(capsys.readouterr().out)
    joined = "\n".join(data["commands"])
    assert "doctor --json" in joined
    assert "landing-receipt" in joined
    assert "submission-pack" in joined


def test_no_write_does_not_create_files(capsys, tmp_path):
    _seed_inputs(tmp_path)
    out = tmp_path / "fixpack"
    adoption_fixpack(_ns(tmp_path, out=str(out), no_write=True))
    capsys.readouterr()
    assert not out.exists()


def test_write_creates_fixpack_files(capsys, tmp_path):
    _seed_inputs(tmp_path)
    out = tmp_path / "fixpack"
    adoption_fixpack(_ns(tmp_path, out=str(out), no_write=False))
    capsys.readouterr()
    assert (out / "adoption-fixpack.json").exists()
    assert (out / "RUN_THIS_FIRST.md").exists()
    assert (out / "copy-paste-agent-prompt.md").exists()
    assert (out / "commands.sh").exists()


def test_privacy_contract_is_local_only(capsys, tmp_path):
    _seed_inputs(tmp_path)
    adoption_fixpack(_ns(tmp_path))
    data = json.loads(capsys.readouterr().out)
    assert data["privacy"]["hidden_telemetry"] is False
    assert data["privacy"]["external_posts"] is False
    assert data["privacy"]["local_files_only"] is True
