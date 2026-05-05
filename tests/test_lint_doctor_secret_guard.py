import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "agentpress.py"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_lint_refuses_sensitive_root_without_reading(tmp_path):
    secret_root = tmp_path / ".ssh"
    secret_root.mkdir()
    (secret_root / "README.md").write_text("PRIVATE KEY should never be read\n", encoding="utf-8")

    result = run_cli("lint", str(secret_root), "--json", "--no-write")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["checked"] == ["secret_path_guard"]
    assert payload["findings"][0]["code"] == "sensitive_root_refused"
    assert "PRIVATE KEY" not in result.stdout
    assert "PRIVATE KEY" not in result.stderr


def test_doctor_refuses_sensitive_root_without_reading(tmp_path):
    secret_root = tmp_path / ".aws"
    secret_root.mkdir()
    (secret_root / "llms.txt").write_text("aws_secret_access_key=example\n", encoding="utf-8")

    result = run_cli("doctor", str(secret_root), "--json")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["security_guard"]["code"] == "sensitive_root_refused"
    assert payload["entrypoints"] == []
    assert "aws_secret_access_key" not in result.stdout
    assert "aws_secret_access_key" not in result.stderr


def test_llms_init_refuses_sensitive_root_without_reading(tmp_path):
    secret_root = tmp_path / ".npmrc"
    secret_root.mkdir()
    (secret_root / "README.md").write_text("//registry.npmjs.org/:_authToken=example\n", encoding="utf-8")

    result = run_cli("llms-init", str(secret_root), "--json")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["checked"] == ["secret_path_guard"]
    assert payload["security_guard"]["code"] == "sensitive_root_refused"
    assert not (secret_root / "llms.txt").exists()
    assert "_authToken" not in result.stdout
    assert "_authToken" not in result.stderr
