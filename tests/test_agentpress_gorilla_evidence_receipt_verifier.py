from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.agentpress_gorilla_evidence_receipt_verifier import build_verifier, local_artifact_path_ok, sample_receipts, verify_receipts

ROOT = Path(__file__).resolve().parents[1]


def test_local_artifact_path_guard_rejects_external_secret_and_parent_paths() -> None:
    assert local_artifact_path_ok("agentpress/evidence/local-step-1.json")
    assert not local_artifact_path_ok("https://example.com/receipt.json")
    assert not local_artifact_path_ok("/tmp/receipt.json")
    assert not local_artifact_path_ok("../receipt.json")
    assert not local_artifact_path_ok("agentpress/evidence/token-receipt.json")


def test_build_verifier_from_wave100_capsule_is_ready() -> None:
    data = build_verifier(ROOT)
    assert data["status"] == "ok"
    assert data["public_push_publish_deploy"] is False
    assert data["jake_explicit_approval_required_for_public_actions"] is True
    assert data["blockers"] == []
    assert data["acceptance_summary"]["all_steps_verified"] is True
    assert data["acceptance_summary"]["accepted_receipts"] == data["acceptance_summary"]["total_receipts"]
    assert data["verified_steps"]


def test_verify_receipts_blocks_hash_exit_and_nonlocal_artifact_failures() -> None:
    capsule = json.loads((ROOT / "agentpress/evidence/agentpress-gorilla-drill-evidence-capsule-wave100.json").read_text())
    bundle = sample_receipts(capsule)
    bundle["step_receipts"][0]["command_sha256"] = "bad"
    bundle["step_receipts"][1]["exit_code"] = 1
    bundle["step_receipts"][2]["generated_local_artifact_paths"] = ["https://example.com/out.json"]
    rows, blockers = verify_receipts(capsule, bundle)
    assert rows[0]["accepted"] is False
    assert "step_1:command_sha256_mismatch" in blockers
    assert "step_2:exit_code_not_zero" in blockers
    assert "step_3:generated_local_artifact_paths_not_local" in blockers


def test_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    out = tmp_path / "verifier.json"
    md = tmp_path / "verifier.md"
    proc = subprocess.run(
        [
            "python3",
            "scripts/agentpress_gorilla_evidence_receipt_verifier.py",
            ".",
            "--out",
            str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out),
            "--markdown-out",
            str(md.relative_to(ROOT)) if md.is_relative_to(ROOT) else str(md),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text())
    assert data["status"] == "ok"
    assert md.read_text().startswith("# AgentPress Gorilla evidence receipt verifier")
