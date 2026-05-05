import json
import subprocess
import sys


def run_cli(*args):
    return subprocess.run([sys.executable, "scripts/agentpress.py", *args], text=True, capture_output=True)


def proof(**overrides):
    data = {
        "agent_id": "outside-agent-1",
        "runtime": "cline",
        "service_id": "agentpress-doctor",
        "capability_id": "doctor",
        "commands_run": ["npx @agent_press/agentpress@rc doctor --json"],
        "artifacts": [{"path": "doctor.json", "sha256": "abc"}],
        "result_status": "pass",
        "redaction_attestation": "no secrets, private prompts, cookies, or local private paths included",
        "transcript": "doctor command completed successfully",
    }
    data.update(overrides)
    return data


def test_external_proof_intake_submit_review_status(tmp_path):
    pack = tmp_path / "proof.json"
    pack.write_text(json.dumps(proof()), encoding="utf-8")
    out = tmp_path / "intake"

    submit = run_cli("external-proof-intake", "submit", "--pack", str(pack), "--submission-id", "p1", "--out", str(out), "--json")
    assert submit.returncode == 0
    assert json.loads(submit.stdout)["decision"] == "submitted"

    review = run_cli("external-proof-intake", "review", "--submission-id", "p1", "--decision", "accept", "--out", str(out), "--json")
    assert review.returncode == 0
    assert json.loads(review.stdout)["submission"]["status"] == "accepted"

    status = run_cli("external-proof-intake", "status", "--out", str(out), "--json")
    payload = json.loads(status.stdout)
    assert payload["counts"]["submitted"] == 1
    assert payload["counts"]["accepted_independent_real"] == 1
    assert payload["counts"]["runtimes"] == {"cline": 1}


def test_external_proof_intake_rejects_self_private_and_secret_markers(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(proof(agent_id="barneywohl-self", transcript="/Volumes/X10/clawd secret api_key")), encoding="utf-8")

    cp = run_cli("external-proof-intake", "submit", "--pack", str(bad), "--out", str(tmp_path / "intake"), "--json")
    assert cp.returncode == 1
    payload = json.loads(cp.stdout)
    assert payload["decision"] == "rejected"
    assert any("blocked private/self/secret marker" in e for e in payload["submission"]["errors"])


def test_external_proof_intake_rejects_missing_transcript_or_commands(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(proof(commands_run=[], transcript="")), encoding="utf-8")

    cp = run_cli("external-proof-intake", "submit", "--pack", str(bad), "--out", str(tmp_path / "intake"), "--json")
    assert cp.returncode == 1
    errors = json.loads(cp.stdout)["submission"]["errors"]
    assert "missing replay transcript or commands_run" in errors


def test_external_proof_intake_blocker_review_counts(tmp_path):
    pack = tmp_path / "proof.json"
    pack.write_text(json.dumps(proof(result_status="blocked")), encoding="utf-8")
    out = tmp_path / "intake"
    assert run_cli("external-proof-intake", "submit", "--pack", str(pack), "--submission-id", "p2", "--out", str(out), "--json").returncode == 0
    assert run_cli("external-proof-intake", "review", "--submission-id", "p2", "--decision", "blocker", "--out", str(out), "--json").returncode == 0
    status = json.loads(run_cli("external-proof-intake", "status", "--out", str(out), "--json").stdout)
    assert status["counts"]["blockers"] == 1
