import argparse
import importlib.util
import json
import pathlib

_SCRIPTS = pathlib.Path(__file__).parent.parent / "scripts"
_SPEC = importlib.util.spec_from_file_location("agentpress", _SCRIPTS / "agentpress.py")
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

safety_preflight = _MOD.safety_preflight
context_budget = _MOD.context_budget
mcp_config_doctor = _MOD.mcp_config_doctor
provider_error_explainer = _MOD.provider_error_explainer


def _safety_args(root, **kw):
    defaults = dict(
        root=str(root),
        manifest="",
        tool_manifest="",
        redaction_path="",
        max_redaction_files=200,
        max_redaction_chars=200000,
        out="/tmp/agentpress-safety-preflight.json",
        base_url="https://example.com/agentpress/",
        no_write=True,
        json=True,
        strict=False,
    )
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def _context_args(root, **kw):
    defaults = dict(
        root=str(root),
        max_files=10,
        max_bytes=10000,
        max_chars=10000,
        source_map="source-map.json",
        freshness="freshness.json",
        require_source_map=True,
        out="/tmp/agentpress-context-budget.json",
        base_url="https://example.com/agentpress/",
        no_write=True,
        json=True,
        strict=False,
    )
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def _mcp_args(**kw):
    defaults = dict(
        config="",
        out="/tmp/agentpress-mcp-config-doctor.json",
        base_url="https://example.com/agentpress/",
        no_write=True,
        json=True,
        strict=False,
    )
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def test_safety_preflight_links_guardrails_without_default_secret_reads(tmp_path, capsys):
    (tmp_path / "README.md").write_text("public docs\n", encoding="utf-8")

    rc = safety_preflight(_safety_args(tmp_path))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["schema_version"] == "2026-05-05.agentpress-safety-preflight.v1"
    assert data["no_secret_reads_by_default"] is True
    check_ids = {row["id"] for row in data["checks"]}
    assert {"secret_permission_preflight", "redaction_check", "tool_file_access_risk_scanner", "sandbox_guard"} <= check_ids
    assert any(row["id"] == "redaction_check" and row["status"] == "guidance_only" for row in data["checks"])


def test_safety_preflight_refuses_sensitive_root_without_echoing_contents(tmp_path, capsys):
    secret_dir = tmp_path / ".ssh"
    secret_dir.mkdir()
    (secret_dir / "id_rsa").write_text("PRIVATE KEY should not appear\n", encoding="utf-8")

    rc = safety_preflight(_safety_args(secret_dir))
    raw = capsys.readouterr().out
    data = json.loads(raw)

    assert rc == 0
    assert data["status"] == "fail_closed"
    assert data["checks"][0]["status"] == "fail_closed"
    assert "PRIVATE KEY" not in raw


def test_context_budget_passes_small_bundle_with_source_map_and_freshness(tmp_path, capsys):
    (tmp_path / "source-map.json").write_text('{"claims":[]}\n', encoding="utf-8")
    (tmp_path / "freshness.json").write_text('{"generated_at":"2026-05-05T00:00:00Z"}\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("short\n", encoding="utf-8")

    rc = context_budget(_context_args(tmp_path))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "ok"
    assert data["actual"]["file_count"] == 3
    assert data["source_map"]["present"] is True


def test_context_budget_reports_exact_remediation_for_bloat_and_missing_maps(tmp_path, capsys):
    for i in range(4):
        (tmp_path / f"file-{i}.txt").write_text("x" * 50, encoding="utf-8")

    rc = context_budget(_context_args(tmp_path, max_files=2, max_bytes=80, max_chars=80))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "needs_remediation"
    codes = {row["code"] for row in data["findings"]}
    assert {"missing_source_map", "too_many_files", "too_many_bytes", "too_many_estimated_chars"} <= codes
    assert any("source-map.json" in item for item in data["exact_remediation"])


def test_mcp_config_doctor_accepts_safe_config(tmp_path, capsys):
    config = tmp_path / "mcp.json"
    config.write_text(json.dumps({
        "mcpServers": {
            "agentpress": {
                "command": "python3",
                "args": ["scripts/agentpress.py", "mcp-catalog-export", "--json"],
                "env": {"AGENTPRESS_TOKEN": "$AGENTPRESS_TOKEN"},
            }
        }
    }), encoding="utf-8")

    rc = mcp_config_doctor(_mcp_args(config=str(config)))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "ok"
    assert data["server_count"] == 1
    assert data["mutated_config"] is False


def test_mcp_config_doctor_flags_duplicates_and_secret_literals_without_echo(tmp_path, capsys):
    config = tmp_path / "mcp.json"
    secret = "sk-live-value-that-should-not-echo"
    config.write_text(json.dumps({
        "servers": [
            {"name": "fs", "command": "node", "env": {"API_KEY": secret}},
            {"name": "fs", "command": "node", "env": {}},
        ]
    }), encoding="utf-8")

    rc = mcp_config_doctor(_mcp_args(config=str(config)))
    raw = capsys.readouterr().out
    data = json.loads(raw)

    assert rc == 0
    assert data["status"] == "fail"
    codes = {row["code"] for row in data["findings"]}
    assert {"duplicate_server_name", "dangerous_env_value_marker"} <= codes
    assert secret not in raw


def test_mcp_config_doctor_flags_invalid_json_without_mutation(tmp_path, capsys):
    config = tmp_path / "mcp.json"
    config.write_text('{"mcpServers": ', encoding="utf-8")

    rc = mcp_config_doctor(_mcp_args(config=str(config)))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "fail"
    assert data["mutated_config"] is False
    assert any(row["code"] == "invalid_json" for row in data["findings"])


def test_provider_error_explainer_points_context_errors_to_context_budget(capsys):
    args = argparse.Namespace(
        error="maximum context length exceeded",
        error_file="",
        provider="auto",
        out="/tmp/provider-error.json",
        base_url="https://example.com/agentpress/",
        no_write=True,
        json=True,
    )
    rc = provider_error_explainer(args)
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    commands = data["remediation_packs"][0]["exact_commands"]
    assert any("context-budget" in command for command in commands)
