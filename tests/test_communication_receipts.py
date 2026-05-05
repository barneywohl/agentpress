import json
import subprocess
import sys


def run_cli(*args):
    return subprocess.run([sys.executable, "scripts/agentpress.py", *args], text=True, capture_output=True)


def test_message_inbox_complete_writes_result_receipt_and_confidential_metadata(tmp_path):
    comms = tmp_path / "comms"
    req = tmp_path / "request.json"
    res = tmp_path / "response.json"
    env = tmp_path / "envelope.json"

    assert run_cli("message", "inbox-init", "--dir", str(comms)).returncode == 0
    assert run_cli("message", "register", "--agent-id", "worker", "--capabilities", "validate_agentpress_bundle", "--dir", str(comms)).returncode == 0
    assert run_cli("message", "create-request", "--capability", "validate_agentpress_bundle", "--task", "validate bundle", "--requester-id", "tester", "--out", str(req)).returncode == 0
    assert run_cli("confidential-message-create", "--from-agent", "tester", "--to-agent", "worker", "--subject", "private context", "--body", "secret context not stored", "--out", str(env), "--json").returncode == 0

    send = run_cli("message", "send", "--to", "worker", "--request", str(req), "--confidential-envelope", str(env), "--dir", str(comms))
    assert send.returncode == 0, send.stderr + send.stdout
    delivery = json.loads(send.stdout)["delivery_id"]
    claimed = run_cli("message", "claim", "--agent-id", "worker", "--message-id", delivery, "--dir", str(comms))
    assert claimed.returncode == 0

    assert run_cli("message", "create-response", "--request", str(req), "--responder-id", "worker", "--status", "completed", "--result-inline", '{"ok":true}', "--out", str(res)).returncode == 0
    done = run_cli("message", "complete", "--agent-id", "worker", "--message-id", delivery, "--response", str(res), "--dir", str(comms))
    assert done.returncode == 0, done.stderr + done.stdout
    payload = json.loads(done.stdout)
    receipt = json.loads((comms / "receipts" / f"{delivery}-result-receipt.json").read_text())
    assert payload["receipt"] == str(comms / "receipts" / f"{delivery}-result-receipt.json")
    assert receipt["response_sha256"]
    assert receipt["privacy"]["confidential_plaintext_stored"] is False
    assert receipt["privacy"]["confidential_envelope"]["body_sha256"]


def test_queue_adapter_kit_includes_inbox_and_confidential_adapters(tmp_path):
    out = tmp_path / "queue"
    cp = run_cli("queue-adapter-kit", "--out", str(out), "--json")
    assert cp.returncode == 0
    manifest = json.loads((out / "manifest.json").read_text())
    assert "static-inbox-adapter.json" in manifest["files"]
    assert "confidential-queue-adapter.json" in manifest["files"]
    assert json.loads((out / "static-inbox-adapter.json").read_text())["receipt_policy"]
    assert json.loads((out / "confidential-queue-adapter.json").read_text())["rules"]


def test_external_proof_intake_writes_receipt_path(tmp_path):
    pack = tmp_path / "proof.json"
    pack.write_text(json.dumps({
        "agent_id": "outside-agent-1",
        "runtime": "cline",
        "service_id": "agentpress-doctor",
        "capability_id": "doctor",
        "commands_run": ["agentpress doctor --json"],
        "artifacts": [{"path": "doctor.json", "sha256": "abc"}],
        "result_status": "pass",
        "redaction_attestation": "no secrets",
        "transcript": "ok",
    }), encoding="utf-8")
    out = tmp_path / "intake"
    cp = run_cli("external-proof-intake", "submit", "--pack", str(pack), "--submission-id", "p-receipt", "--out", str(out), "--json")
    assert cp.returncode == 0, cp.stderr + cp.stdout
    payload = json.loads(cp.stdout)
    receipt_path = out / "receipts" / "p-receipt-intake-receipt.json"
    assert payload["submission"]["receipt_path"] == str(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    assert receipt["submission_id"] == "p-receipt"
    assert receipt["decision"] == "submitted"
