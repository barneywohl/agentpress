import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, str(ROOT / "scripts" / "agentpress.py")]


def run(*args):
    return subprocess.run(CLI + list(args), cwd=ROOT, text=True, capture_output=True, check=True)


def test_mesh_register_dry_run_and_duplicate_guard(tmp_path):
    out = tmp_path / "known-agents.json"
    first = run(
        "mesh", "register",
        "--id", "cline-local",
        "--kind", "cline",
        "--capabilities", "code-edit,terminal,mcp",
        "--contract-url", "./agentpress/contracts/cline-local.json",
        "--out", str(out),
        "--json",
    )
    payload = json.loads(first.stdout)
    assert payload["status"] == "ok"
    assert out.exists()
    dup = subprocess.run(
        CLI + [
            "mesh", "register", "--id", "cline-local", "--kind", "cline", "--capabilities", "terminal", "--contract-url", "./x.json", "--out", str(out), "--json"
        ], cwd=ROOT, text=True, capture_output=True
    )
    assert dup.returncode != 0
    assert "duplicate" in dup.stdout
    dry = run(
        "mesh", "register", "--id", "cline-local", "--kind", "cline", "--capabilities", "terminal", "--contract-url", "./x.json", "--out", str(out), "--replace", "--dry-run", "--json"
    )
    assert json.loads(dry.stdout)["dry_run"] is True


def test_first_contact_audit_no_network(tmp_path):
    out = tmp_path / "first-contact.json"
    res = run("first-contact", "audit", "--no-network", "--out", str(out), "--json")
    payload = json.loads(res.stdout)
    assert payload["status"] == "ok"
    assert payload["receipt_sha256"]
    assert out.exists()
    assert payload["package_channels"]["npm"]["rc"]


def test_result_protocol_secret_refusal_and_validate(tmp_path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"status":"ok"}\n')
    result = tmp_path / "result.json"
    run("result", "finalize", "--kind", "proof", "--claim", "proof claim", "--file", str(evidence), "--step", "agentpress doctor --json", "--out", str(result), "--json")
    valid = run("result", "validate", str(result), "--strict", "--json")
    assert json.loads(valid.stdout)["status"] == "ok"
    secret = tmp_path / "api_token.txt"
    secret.write_text("x")
    bad = subprocess.run(CLI + ["result", "add-file", str(secret), "--json"], cwd=ROOT, text=True, capture_output=True)
    assert bad.returncode != 0
    assert "secret-looking" in bad.stdout


def test_compat_smoke_priority_targets(tmp_path):
    for target in ["cline", "roo", "openhands", "mcp"]:
        out = tmp_path / f"{target}.json"
        res = run("compat", "smoke", "--target", target, "--out", str(out), "--json")
        payload = json.loads(res.stdout)
        assert payload["status"] == "ok"
        assert out.exists()
        assert payload["receipt_path"] == str(out)
