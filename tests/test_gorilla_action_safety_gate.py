import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, str(ROOT / "scripts" / "agentpress.py")]


def run(*args):
    return subprocess.run(CLI + list(args), cwd=ROOT, text=True, capture_output=True, check=True)


def test_gorilla_action_safety_gate_classifies_queue(tmp_path):
    out = tmp_path / "gate.json"
    cp = run("gorilla-action-safety-gate", "--out", str(out), "--json")
    payload = json.loads(cp.stdout)
    assert payload["schema_version"] == "2026-05-05.agentpress-gorilla-external-action-safety-gate.v1"
    assert payload["counts"]["safe_internal"] >= 2
    assert payload["counts"]["approval_required_public"] >= 6
    assert payload["counts"]["prohibited_spam_security_risk"] >= 1
    assert out.exists()

    decisions = {str(d["id"]): d for d in payload["decisions"]}
    assert decisions["5"]["classification"] == "prohibited_spam_security_risk"
    assert "do_not_post" in decisions["5"]["required_controls"]
    assert decisions["1"]["classification"] == "approval_required_public"
    assert "explicit_human_approval_of_exact_target_and_draft" in decisions["1"]["required_controls"]


def test_gorilla_action_safety_gate_ad_hoc_deterministic_classes():
    safe = run(
        "gorilla-action-safety-gate",
        "--no-write",
        "--action-json",
        json.dumps({"action": "use internally for feature prioritization"}),
        "--json",
    )
    safe_payload = json.loads(safe.stdout)
    assert safe_payload["decisions"][-1]["classification"] == "safe_internal"
    assert safe_payload["decisions"][-1]["allowed_to_execute"] is True

    public = run(
        "gorilla-action-safety-gate",
        "--no-write",
        "--action-json",
        json.dumps({"action": "comment on a GitHub issue", "url": "https://github.com/example/repo/issues/1", "draft": "targeted fixture"}),
        "--json",
    )
    public_payload = json.loads(public.stdout)
    assert public_payload["decisions"][-1]["classification"] == "approval_required_public"
    assert public_payload["decisions"][-1]["allowed_to_execute"] is False

    bad = run(
        "gorilla-action-safety-gate",
        "--no-write",
        "--action-json",
        json.dumps({"action": "mass post security exploit with scraped DMs and token examples"}),
        "--json",
    )
    bad_payload = json.loads(bad.stdout)
    assert bad_payload["decisions"][-1]["classification"] == "prohibited_spam_security_risk"
    assert bad_payload["decisions"][-1]["allowed_to_execute"] is False
