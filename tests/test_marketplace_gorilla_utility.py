import json
import subprocess
import sys


def run_cli(*args):
    return subprocess.run([sys.executable, "scripts/agentpress.py", *args], text=True, capture_output=True)


def test_marketplace_exposes_gorilla_install_run_proof_flow(tmp_path):
    out = tmp_path / "marketplace.json"
    cp = run_cli("marketplace", "--out", str(out), "--capability", "gorilla-utility-pack", "--json")
    assert cp.returncode == 0, cp.stderr
    payload = json.loads(cp.stdout)
    services = {svc["service_id"]: svc for svc in payload["services"]}

    assert "gorilla-utility-execution-queue" in services
    assert "gorilla-utility-cline-provider-repro" in services
    assert payload["service_count"] >= 6

    queue = services["gorilla-utility-execution-queue"]
    assert queue["install_run_proof_commands"]["install"] == "python3 scripts/agentpress.py gorilla-utility-pack --json"
    assert "execution-queue.json" in queue["install_run_proof_commands"]["run"]
    assert queue["safety"]["external_writes"] is False
    assert "Human approval required" in queue["safety"]["external_execution_gate"]

    pack = services["gorilla-utility-cline-provider-repro"]
    flow = pack["install_run_proof_commands"]
    assert flow["run"] == "python3 scripts/agentpress.py provider-adapter-repro-pack --host cline --provider claude_code --json"
    assert flow["proof_finalize"].startswith("python3 scripts/agentpress.py result finalize")
    assert flow["proof_validate"].startswith("python3 scripts/agentpress.py result validate")
    guardrails = " ".join(pack["safety"]["no_spam_guardrails"])
    assert "No mass posting" in guardrails
    assert "explicit human approval" in guardrails
