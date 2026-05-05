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
    assert checks["npm_package_budget"]["status"] == "pass"
    assert "size=" in checks["npm_package_budget"]["detail"]


def test_release_promote_checklist_blocks_oversized_npm_package_budget():
    cp = run_cli(
        "release-promote-checklist",
        "--no-network",
        "--no-write",
        "--json",
        "--strict",
        "--max-npm-package-bytes",
        "1",
    )
    assert cp.returncode == 1
    payload = json.loads(cp.stdout)
    assert "npm_package_budget" in payload["blocking_checks"]
    checks = {check["name"]: check for check in payload["checks"]}
    assert checks["npm_package_budget"]["status"] == "blocked"


def test_release_promote_checklist_no_network_skips_live_registry_probe():
    cp = run_cli("release-promote-checklist", "--no-network", "--no-write", "--json")
    assert cp.returncode == 0
    payload = json.loads(cp.stdout)
    check_names = {check["name"] for check in payload["checks"]}
    assert "npm_dist_tags" not in check_names
    assert payload["promotion_allowed"] is False


def test_release_promote_checklist_writes_evidence_bundle(tmp_path):
    bundle = tmp_path / "bundle"
    cp = run_cli("release-promote-checklist", "--no-network", "--json", "--evidence-bundle-out", str(bundle))
    assert cp.returncode == 0
    payload = json.loads(cp.stdout)
    assert payload["evidence_bundle"] == str(bundle)
    manifest = json.loads((bundle / "release-evidence-bundle.json").read_text())
    assert manifest["schema_version"] == "2026-05-05.agentpress-release-evidence-bundle.v1"
    assert manifest["source_checklist"] == "release-promote-checklist.json"
    names = {item["name"] for item in manifest["artifacts"]}
    assert "release_promote_checklist" in names
    assert "independent_external_proof" in names


def test_release_promote_checklist_verify_bundle_fails_missing_or_blocked(tmp_path):
    missing = run_cli("release-promote-checklist", "--verify-bundle", str(tmp_path / "missing"), "--no-write", "--json", "--strict")
    assert missing.returncode == 1
    assert "bundle_manifest" in json.loads(missing.stdout)["blocking_checks"]

    bundle = tmp_path / "bundle"
    run_cli("release-promote-checklist", "--no-network", "--json", "--evidence-bundle-out", str(bundle))
    verify = run_cli("release-promote-checklist", "--verify-bundle", str(bundle), "--no-write", "--json", "--strict")
    assert verify.returncode == 1
    payload = json.loads(verify.stdout)
    assert payload["status"] == "blocked"
    assert "independent_external_proof" in payload["blocking_checks"]
    assert "rflo_review" in payload["blocking_checks"]
