import argparse
import importlib.util
import json
import pathlib

_SCRIPTS = pathlib.Path(__file__).parent.parent / "scripts"
_SPEC = importlib.util.spec_from_file_location("agentpress", _SCRIPTS / "agentpress.py")
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

tool_contract_check = _MOD.tool_contract_check
provider_error_explainer = _MOD.provider_error_explainer


def _args(**kwargs):
    defaults = {
        "manifest": "",
        "sample_result": "",
        "out": "/tmp/agentpress-tool-contract-check.json",
        "base_url": "https://example.com/agentpress/",
        "require_text_mirror": True,
        "no_write": True,
        "json": True,
        "strict": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_builtin_tool_contract_sample_passes(capsys):
    rc = tool_contract_check(_args())
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["schema_version"] == "2026-05-05.agentpress-tool-contract-check.v1"
    assert data["status"] == "ok"
    assert data["tool_count"] == 1


def test_mcp_tool_without_input_schema_fails_with_remediation(tmp_path, capsys):
    manifest = tmp_path / "tools.json"
    manifest.write_text(json.dumps({
        "tools": [
            {
                "name": "bad_tool",
                "description": "Missing input schema",
                "outputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            }
        ]
    }), encoding="utf-8")

    rc = tool_contract_check(_args(manifest=str(manifest)))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "fail"
    assert any(f["code"] == "missing_input_schema" for f in data["findings"])
    assert any("inputSchema" in item for item in data["exact_remediation"])


def test_output_schema_validates_structured_content_sample(tmp_path, capsys):
    manifest = tmp_path / "tools.json"
    manifest.write_text(json.dumps({
        "tools": [
            {
                "name": "weather",
                "description": "Get weather",
                "inputSchema": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
                "outputSchema": {
                    "type": "object",
                    "properties": {"temperature": {"type": "number"}, "conditions": {"type": "string"}},
                    "required": ["temperature", "conditions"],
                },
            }
        ]
    }), encoding="utf-8")
    sample = tmp_path / "result.json"
    sample.write_text(json.dumps({
        "result": {
            "content": [{"type": "text", "text": "{\"temperature\":22.5,\"conditions\":\"clear\"}"}],
            "structuredContent": {"temperature": 22.5, "conditions": "clear"},
        }
    }), encoding="utf-8")

    rc = tool_contract_check(_args(manifest=str(manifest), sample_result=str(sample)))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "ok"
    assert data["tools"][0]["has_structured_result_sample"] is True


def test_output_schema_mismatch_reports_schema_errors(tmp_path, capsys):
    manifest = tmp_path / "tools.json"
    manifest.write_text(json.dumps({
        "tools": [
            {
                "name": "weather",
                "description": "Get weather",
                "inputSchema": {"type": "object", "properties": {}},
                "outputSchema": {
                    "type": "object",
                    "properties": {"temperature": {"type": "number"}, "conditions": {"type": "string"}},
                    "required": ["temperature", "conditions"],
                },
            }
        ]
    }), encoding="utf-8")
    sample = tmp_path / "result.json"
    sample.write_text(json.dumps({
        "result": {
            "content": [{"type": "text", "text": "{\"temperature\":\"hot\"}"}],
            "structuredContent": {"temperature": "hot"},
        }
    }), encoding="utf-8")

    rc = tool_contract_check(_args(manifest=str(manifest), sample_result=str(sample)))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "fail"
    assert any(f["code"] == "structured_content_schema_mismatch" for f in data["findings"])
    assert data["tools"][0]["schema_errors"]


def test_cli_template_without_json_is_needs_remediation(tmp_path, capsys):
    manifest = tmp_path / "tools.json"
    manifest.write_text(json.dumps({
        "tools": [
            {
                "name": "agentpress.bundle",
                "description": "Generate a bundle",
                "command": "python3 scripts/agentpress.py bundle docs --out out",
            }
        ]
    }), encoding="utf-8")

    rc = tool_contract_check(_args(manifest=str(manifest)))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "needs_remediation"
    assert any(f["code"] == "command_missing_json_flag" for f in data["findings"])


def test_cli_template_without_json_can_declare_file_output_contract(tmp_path, capsys):
    manifest = tmp_path / "tools.json"
    manifest.write_text(json.dumps({
        "tools": [
            {
                "name": "agentpress.bundle",
                "description": "Generate a bundle",
                "command": "python3 scripts/agentpress.py bundle docs --out out",
                "machine_output": False,
                "output_contract": "writes a bundle directory; validate with verify --json",
            }
        ]
    }), encoding="utf-8")

    rc = tool_contract_check(_args(manifest=str(manifest)))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "ok"
    assert data["findings"] == []


def test_refuses_sensitive_manifest_without_reading(tmp_path, capsys):
    secret_dir = tmp_path / ".ssh"
    secret_dir.mkdir()
    secret_manifest = secret_dir / "tools.json"
    secret_manifest.write_text("PRIVATE KEY should not be read", encoding="utf-8")

    rc = tool_contract_check(_args(manifest=str(secret_manifest)))
    raw = capsys.readouterr().out
    data = json.loads(raw)

    assert rc == 0
    assert data["status"] == "fail"
    assert any(f["code"] == "manifest_sensitive_path_refused" for f in data["findings"])
    assert "PRIVATE KEY" not in raw


def test_provider_error_explainer_routes_tool_errors_to_contract_check(capsys):
    args = argparse.Namespace(
        error="invalid tool call schema",
        error_file="",
        provider="auto",
        out="/tmp/provider-error.json",
        base_url="https://example.com/agentpress/",
        no_write=True,
        json=True,
    )

    rc = provider_error_explainer(args)
    data = json.loads(capsys.readouterr().out)
    commands = data["remediation_packs"][0]["exact_commands"]

    assert rc == 0
    assert any("tool-contract-check" in command for command in commands)
