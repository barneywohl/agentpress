"""End-to-end tests for the v1.0 Python CLI.

Mirrors tests/cli.test.mjs as closely as possible. Spawns the installed
`agentpress` console script and checks stdout/stderr/exit.

Requires `agentpress-static` (this package) installed in the test env,
e.g. via `pip install -e .` in a venv with `agentpress-core` also installed.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

AGENTPRESS = shutil.which("agentpress") or "agentpress"


def run(args, cwd=None, env_extra=None, input_text=None):
    env = {**os.environ, "AGENTPRESS_LEGACY_QUIET": "1"}
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [AGENTPRESS, *args],
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
        input=input_text,
    )


@pytest.fixture
def sandbox(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/test-org/test-repo.git\n'
    )
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "test-pkg", "author": "A <a@example.com>"})
    )
    return tmp_path


def test_top_help_shows_only_four_verbs():
    r = run([])
    assert r.returncode == 0
    for verb in ("init", "lint", "doctor", "receipt", "legacy"):
        assert verb in r.stdout
    for bloat in ("gorilla", "marketplace", "china", "mission-keeper"):
        assert bloat.lower() not in r.stdout.lower()


def test_version_flag():
    r = run(["--version"])
    assert r.returncode == 0
    import re
    assert re.match(r"^\d+\.\d+\.\d+", r.stdout.strip())


def test_unknown_command_exits_1():
    r = run(["nonexistent"])
    assert r.returncode == 1
    assert "Unknown command" in r.stderr
    assert "Traceback" not in r.stderr


def test_lint_in_empty_dir_file_not_found(sandbox: Path):
    r = run(["lint"], cwd=sandbox)
    assert r.returncode == 3
    combined = r.stderr + r.stdout
    assert "agents.txt not found" in combined
    assert "agentpress init" in combined


def test_init_non_interactive_writes_valid_file(sandbox: Path):
    r1 = run(["init", "--non-interactive"], cwd=sandbox)
    assert r1.returncode == 0, r1.stderr
    assert (sandbox / "agents.txt").exists()
    body = (sandbox / "agents.txt").read_text()
    assert "[meta]" in body
    assert "spec_version = 1.0" in body
    r2 = run(["lint"], cwd=sandbox)
    assert r2.returncode == 0
    assert "valid" in r2.stdout


def test_init_refuses_overwrite_without_force(sandbox: Path):
    run(["init", "--non-interactive"], cwd=sandbox)
    r = run(["init", "--non-interactive"], cwd=sandbox)
    assert r.returncode == 1
    assert "already exists" in r.stderr


def test_init_force_overwrites(sandbox: Path):
    run(["init", "--non-interactive"], cwd=sandbox)
    r = run(["init", "--non-interactive", "--force"], cwd=sandbox)
    assert r.returncode == 0


def test_lint_json_returns_parseable_with_ok_flag(sandbox: Path):
    run(["init", "--non-interactive"], cwd=sandbox)
    r = run(["lint", "--json"], cwd=sandbox)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["spec_version"] == "1.0"


def test_lint_malformed_exits_1(sandbox: Path):
    (sandbox / "agents.txt").write_text("[meta]\nspec_version = 1.0\n")
    r = run(["lint"], cwd=sandbox)
    assert r.returncode == 1
    combined = r.stdout + r.stderr
    assert "error" in combined.lower()
    assert "Traceback" not in combined


def test_doctor_all_pass_after_init(sandbox: Path):
    run(["init", "--non-interactive"], cwd=sandbox)
    r = run(["doctor"], cwd=sandbox)
    assert r.returncode == 0
    assert "System healthy" in r.stdout


def test_doctor_json_returns_structured_output(sandbox: Path):
    run(["init", "--non-interactive"], cwd=sandbox)
    r = run(["doctor", "--json"], cwd=sandbox)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert isinstance(data["checks"], list)
    assert len(data["checks"]) >= 5


def test_receipt_stdout_only_emits_valid_json(sandbox: Path):
    run(["init", "--non-interactive"], cwd=sandbox)
    r = run(["receipt", "--stdout-only"], cwd=sandbox)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["schema_version"] == "agentpress-receipt.v1"
    import re
    assert re.match(r"^[a-f0-9]{64}$", data["agents_txt_sha256"])
    assert data["validation"]["ok"] is True
    assert re.match(r"^rcpt_[a-f0-9]{12}$", data["receipt_id"])


def test_receipt_writes_file_when_not_stdout_only(sandbox: Path):
    run(["init", "--non-interactive"], cwd=sandbox)
    r = run(["receipt"], cwd=sandbox)
    assert r.returncode == 0
    receipts_dir = sandbox / "agentpress" / "receipts"
    assert receipts_dir.exists()
    files = list(receipts_dir.glob("rcpt_*.json"))
    assert len(files) >= 1


def test_receipt_fails_on_invalid_agents_txt(sandbox: Path):
    (sandbox / "agents.txt").write_text("[meta]\nspec_version = 1.0\n")
    r = run(["receipt"], cwd=sandbox)
    assert r.returncode == 1
    combined = r.stdout + r.stderr
    assert ("error" in combined.lower()) or ("Run `agentpress lint`" in combined)


def test_every_verb_help_exits_zero():
    for verb in ("init", "lint", "doctor", "receipt"):
        r = run([verb, "--help"])
        assert r.returncode == 0, f"{verb} --help failed: {r.stderr}"
        assert f"agentpress {verb}".lower() in r.stdout.lower()
