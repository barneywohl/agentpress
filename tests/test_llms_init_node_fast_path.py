"""
Tests for the Node-native llms-init fast path in bin/agentpress.js.

Validates that `agentpress llms-init <dir>` works without Python being available,
creates minimal llms.txt and .well-known/agentpress.json, and is idempotent.
"""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin" / "agentpress.js"
NO_PYTHON_ENV = {**os.environ, "PYTHON": "/nonexistent/python3-absent"}


def test_llms_init_creates_files_in_empty_dir(tmp_path):
    result = subprocess.run(
        ["node", str(BIN), "llms-init", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["status"] == "ok"
    assert data["mode"] == "node-fast-path"
    assert "llms.txt" in data["created"]
    assert ".well-known/agentpress.json" in data["created"]
    assert data["errors"] == []
    assert (tmp_path / "llms.txt").exists()
    assert (tmp_path / ".well-known" / "agentpress.json").exists()


def test_llms_init_llms_txt_content(tmp_path):
    subprocess.run(
        ["node", str(BIN), "llms-init", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    content = (tmp_path / "llms.txt").read_text()
    assert "llms.txt" in content
    assert "agentpress" in content.lower()


def test_llms_init_well_known_json_is_valid(tmp_path):
    subprocess.run(
        ["node", str(BIN), "llms-init", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    wk_data = json.loads((tmp_path / ".well-known" / "agentpress.json").read_text())
    assert wk_data["schema_version"] == "2026-05-05.agentpress-minimal-entrypoint.v1"
    assert wk_data["commands"]["doctor"] == "agentpress doctor . --json"
    assert "name" in wk_data


def test_llms_init_skips_existing_llms_txt(tmp_path):
    original = "# my existing llms.txt\n"
    (tmp_path / "llms.txt").write_text(original)
    result = subprocess.run(
        ["node", str(BIN), "llms-init", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert "llms.txt" in data["skipped"]
    assert (tmp_path / "llms.txt").read_text() == original


def test_llms_init_idempotent_when_all_exist(tmp_path):
    subprocess.run(
        ["node", str(BIN), "llms-init", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    result2 = subprocess.run(
        ["node", str(BIN), "llms-init", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
    )
    assert result2.returncode == 0, result2.stderr
    data2 = json.loads(result2.stdout)
    assert data2["status"] == "already_exists"
    assert data2["created"] == []


def test_llms_init_no_python_required(tmp_path):
    """llms-init must succeed even when Python is not available."""
    result = subprocess.run(
        ["node", str(BIN), "llms-init", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        env=NO_PYTHON_ENV,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["status"] == "ok"
    assert (tmp_path / "llms.txt").exists()
    assert (tmp_path / ".well-known" / "agentpress.json").exists()


def test_llms_init_default_dir_not_absolute_crash(tmp_path):
    """Passing no dir arg (defaults to '.') must not crash."""
    result = subprocess.run(
        ["node", str(BIN), "llms-init", "--json"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["status"] in ("ok", "already_exists")


def test_llms_init_accepts_flags_before_dir(tmp_path):
    result = subprocess.run(
        ["node", str(BIN), "llms-init", "--json", "--title", "Demo Repo", str(tmp_path)],
        capture_output=True,
        text=True,
        env=NO_PYTHON_ENV,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["status"] == "ok"
    wk_data = json.loads((tmp_path / ".well-known" / "agentpress.json").read_text())
    assert wk_data["name"] == "Demo Repo"


def test_llms_init_refuses_sensitive_root_without_reading(tmp_path):
    secret_root = tmp_path / ".ssh"
    secret_root.mkdir()
    (secret_root / "README.md").write_text("PRIVATE KEY should not be exposed\n", encoding="utf-8")

    result = subprocess.run(
        ["node", str(BIN), "llms-init", str(secret_root), "--json"],
        capture_output=True,
        text=True,
        env=NO_PYTHON_ENV,
    )

    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["status"] == "fail"
    assert data["security_guard"]["code"] == "sensitive_root_refused"
    assert not (secret_root / "llms.txt").exists()
    assert "PRIVATE KEY" not in result.stdout
    assert "PRIVATE KEY" not in result.stderr


def test_node_doctor_no_python_checks_generated_files(tmp_path):
    subprocess.run(
        ["node", str(BIN), "llms-init", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        env=NO_PYTHON_ENV,
        check=True,
    )
    result = subprocess.run(
        ["node", str(BIN), "doctor", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        env=NO_PYTHON_ENV,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["status"] == "ok"
    assert data["mode"] == "node-fast-path"
    assert len(data["entrypoints"]) == 2


def test_node_doctor_no_python_reports_missing_entrypoints(tmp_path):
    result = subprocess.run(
        ["node", str(BIN), "doctor", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        env=NO_PYTHON_ENV,
    )
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["status"] == "fail"
    assert "missing llms.txt" in data["errors"]
    commands = "\n".join(step["command"] for step in data["next_steps"])
    assert "llms-init" in commands


def test_node_doctor_refuses_sensitive_root_without_reading(tmp_path):
    secret_root = tmp_path / ".aws"
    secret_root.mkdir()
    (secret_root / "llms.txt").write_text("aws_secret_access_key=example\n", encoding="utf-8")

    result = subprocess.run(
        ["node", str(BIN), "doctor", str(secret_root), "--json"],
        capture_output=True,
        text=True,
        env=NO_PYTHON_ENV,
    )

    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["status"] == "fail"
    assert data["security_guard"]["code"] == "sensitive_root_refused"
    assert "aws_secret_access_key" not in result.stdout
    assert "aws_secret_access_key" not in result.stderr
