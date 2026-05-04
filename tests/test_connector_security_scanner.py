import argparse
import importlib.util
import json
import pathlib

_SCRIPTS = pathlib.Path(__file__).parent.parent / "scripts"
_SPEC = importlib.util.spec_from_file_location("agentpress", _SCRIPTS / "agentpress.py")
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

connector_security_scanner = _MOD.connector_security_scanner


def _args(tmp_path, **kwargs):
    defaults = {
        "manifest": None,
        "out": str(tmp_path / "connector-security-scanner.json"),
        "base_url": "https://example.com/agentpress/",
        "no_write": True,
        "json": True,
        "strict": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_builtin_sample_is_clean(tmp_path, capsys):
    rc = connector_security_scanner(_args(tmp_path))
    data = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert data["status"] == "ok"
    assert data["finding_count"] == 0


def test_flags_secret_auth_transport_env_and_dangerous_tools(tmp_path, capsys):
    manifest = tmp_path / "bad-connector.json"
    manifest.write_text(json.dumps({
        "connectors": [{
            "id": "bad-mcp",
            "transport": "magicpipe",
            "api_key": "sk-1234567890abcdef",
            "env": ["OPENAI_API_KEY"],
            "tools": [
                {"name": "deploy_shell", "effects": ["write", "external"]},
                {"name": "delete_user"}
            ]
        }]
    }))
    rc = connector_security_scanner(_args(tmp_path, manifest=str(manifest), strict=True))
    data = json.loads(capsys.readouterr().out)
    rule_ids = {f["rule_id"] for f in data["findings"]}
    assert rc == 1
    assert data["status"] == "fail"
    assert {"secret_literal", "missing_auth_mode", "unknown_transport", "env_var_unscoped", "r4_without_approval", "dangerous_tool"}.issubset(rule_ids)
    assert "sk-1234567890abcdef" not in json.dumps(data)


def test_safe_connector_with_scoped_env_and_approval_passes(tmp_path, capsys):
    manifest = tmp_path / "safe-connector.json"
    manifest.write_text(json.dumps({
        "connectors": [{
            "id": "safe-mcp",
            "transport": "stdio",
            "auth_mode": "env_token",
            "env": [{"name": "SAFE_API_TOKEN", "scope": "read-only catalog fetch"}],
            "tools": [{"name": "deploy_preview", "effects": ["write"], "risk_level": "R4", "approval_ref": "human-approved-preview"}]
        }]
    }))
    rc = connector_security_scanner(_args(tmp_path, manifest=str(manifest), strict=True))
    data = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert data["status"] == "ok"
    assert data["finding_count"] == 0
