import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin" / "agentpress.js"
NO_PYTHON_ENV = {**os.environ, "PYTHON": "/nonexistent/python3-agentpress-test"}


def test_non_fast_path_command_gets_json_remediation_without_python():
    result = subprocess.run(
        ["node", str(BIN), "validate", ".", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=NO_PYTHON_ENV,
    )
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["schema_version"] == "2026-05-05.agentpress-node-no-python-command.v1"
    assert data["command"] == "validate"
    assert data["status"] == "fail"
    assert data["next_steps"]
    assert data["full_cli_requires"] == "Python >=3.10"
    assert result.stderr == ""


def test_doctor_fast_path_gets_json_without_python():
    result = subprocess.run(
        ["node", str(BIN), "doctor", ".", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=NO_PYTHON_ENV,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["schema_version"].startswith("2026-05-05.agentpress-node-fast-doctor.v")
    assert data["mode"] == "node-fast-path"
    assert data["next_steps"]
    assert result.stderr == ""


def test_no_python_fallback_check_cli_passes(tmp_path):
    out = tmp_path / "no-python.json"
    result = subprocess.run(
        ["python3", "scripts/agentpress.py", "no-python-fallback-check", ".", "--out", str(out), "--json", "--strict"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    data = json.loads(result.stdout)
    assert data["status"] == "ok"
    assert data["fail_count"] == 0
    assert [r["command"] for r in data["results"]] == ["doctor", "validate", "verify", "agent-onboard"]
    assert all(r["status"] == "pass" for r in data["results"])
