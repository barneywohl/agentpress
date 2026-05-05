import argparse
import importlib.util
import json
import pathlib

_SCRIPTS = pathlib.Path(__file__).parent.parent / "scripts"
_SPEC = importlib.util.spec_from_file_location("agentpress", _SCRIPTS / "agentpress.py")
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

cli_gap_audit = _MOD.cli_gap_audit


def test_cli_gap_audit_current_repo_has_no_command_drift(capsys, tmp_path):
    root = pathlib.Path(__file__).parent.parent
    rc = cli_gap_audit(argparse.Namespace(root=str(root), out=str(tmp_path / "cli-gap.json"), base_url="https://example.com/agentpress/", no_write=True, json=True, strict=True))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "ok"
    assert data["parser_no_dispatch"] == []
    assert data["dispatch_no_parser"] == []
    assert data["tool_contract_check"]["status"] == "ok"
    assert data["tool_contract_check"]["fail_count"] == 0
    assert data["tool_contract_check"]["warn_count"] == 0
