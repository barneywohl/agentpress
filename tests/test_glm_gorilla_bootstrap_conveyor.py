import json
import subprocess
import sys


def run_cli(*args):
    return subprocess.run([sys.executable, "scripts/agentpress.py", *args], text=True, capture_output=True)


def test_glm_gorilla_bootstrap_conveyor_from_receipt(tmp_path):
    receipt = tmp_path / "glm-receipts.json"
    receipt.write_text(json.dumps({
        "kit_build_records": [{
            "id": "glm-demo-kit",
            "runtime": "glm",
            "status": "validated",
            "kit_path": "agentpress/examples/api-docs-handoff"
        }]
    }))
    out = tmp_path / "packet.json"
    cp = run_cli("glm-gorilla-bootstrap-conveyor", "--receipt", str(receipt), "--out", str(out), "--json")
    assert cp.returncode == 0, cp.stderr
    payload = json.loads(cp.stdout)
    assert payload["schema_version"] == "2026-05-10.agentpress-glm-gorilla-bootstrap-conveyor.v1"
    assert payload["record_count"] == 1
    assert payload["materialized_validated_status"]["validated_count"] == 1
    assert payload["selected_kit_path"] == "agentpress/examples/api-docs-handoff"
    assert payload["first_useful_command"].startswith("python3 scripts/agentpress.py kit validate")
    assert "proof-capture" in payload["proof_command"]
    assert payload["safety"]["external_writes"] is False
    assert out.exists()


def test_glm_gorilla_bootstrap_conveyor_no_write_fallback(tmp_path):
    out = tmp_path / "packet.json"
    cp = run_cli("glm-gorilla-bootstrap-conveyor", "--out", str(out), "--no-write", "--json")
    assert cp.returncode == 0, cp.stderr
    payload = json.loads(cp.stdout)
    assert payload["receipt_source"] == "inline_empty_demo"
    assert payload["record_count"] == 0
    assert "gorilla-utility-pack" in payload["first_useful_command"]
    assert not out.exists()
