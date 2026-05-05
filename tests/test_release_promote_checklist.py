import json
import subprocess
import sys


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "scripts/agentpress.py", *args],
        text=True,
        capture_output=True,
    )


def test_release_promote_checklist_strict_is_fail_closed_without_required_proofs():
    cp = run_cli("release-promote-checklist", "--no-network", "--no-write", "--json", "--strict")
    assert cp.returncode == 1
    payload = json.loads(cp.stdout)
    assert payload["schema_version"] == "2026-05-05.agentpress-release-promote-checklist.v1"
    assert payload["status"] == "blocked"
    assert payload["promotion_allowed"] is False
    assert payload["decision"].startswith("Do not promote rc to latest")
    assert "independent_external_proof" in payload["blocking_checks"]
    checks = {check["name"]: check for check in payload["checks"]}
    assert checks["cli_gap_audit"]["status"] == "pass"
    assert checks["tool_contract_check"]["status"] == "pass"
    assert checks["no_python_fallback_check"]["status"] == "pass"


def test_release_promote_checklist_no_network_skips_live_registry_probe():
    cp = run_cli("release-promote-checklist", "--no-network", "--no-write", "--json")
    assert cp.returncode == 0
    payload = json.loads(cp.stdout)
    check_names = {check["name"] for check in payload["checks"]}
    assert "npm_dist_tags" not in check_names
    assert payload["promotion_allowed"] is False
