import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, str(ROOT / "scripts" / "agentpress.py")]


def run(*args):
    return subprocess.run(CLI + list(args), cwd=ROOT, text=True, capture_output=True)


def test_marketplace_safety_gate_allows_local_no_spend_and_fulfillment(tmp_path):
    quote = tmp_path / "quote.json"
    proof = tmp_path / "proof.json"
    gate = tmp_path / "gate.json"
    receipt = tmp_path / "fulfill.json"
    proof.write_text('{"proof":"local fixture only"}\n', encoding="utf-8")

    cp = run(
        "marketplace-compare",
        "--capability",
        "self-test",
        "--budget-cap",
        "0",
        "--out",
        str(quote),
        "--json",
    )
    assert cp.returncode == 0, cp.stderr

    cp = run("marketplace-safety-gate", "--quote", str(quote), "--out", str(gate), "--json")
    assert cp.returncode == 0, cp.stderr
    payload = json.loads(cp.stdout)
    assert payload["status"] == "safe_local_no_spend"
    assert payload["decision"]["allowed_to_fulfill_locally"] is True
    assert payload["decision"]["external_side_effects_allowed"] is False

    cp = run("marketplace-fulfill", "--quote", str(quote), "--proof", str(proof), "--out", str(receipt), "--json")
    assert cp.returncode == 0, cp.stderr
    fulfillment = json.loads(cp.stdout)
    assert fulfillment["status"] == "fulfilled_local_no_spend"
    assert fulfillment["safety_gate"]["classification"] == "safe_local_no_spend"
    assert fulfillment["payment"]["live_payment_executed"] is False


def test_marketplace_safety_gate_fails_closed_for_spend_secrets_publish_deploy_messages(tmp_path):
    quote = tmp_path / "quote.json"
    quote.write_text('{"services":[],"best_service":{}}\n', encoding="utf-8")
    risky = {
        "service_id": "risky-provider",
        "title": "Risky paid deploy outreach",
        "command": "curl https://api.example.test && npm publish && vercel deploy && gh issue comment 1 --body hi",
        "capabilities": ["deploy", "external message"],
        "pricing": {"payment_required": True, "currency": "USD"},
        "quote_simulation": {"payment_required": True, "quoted_amount": 5, "budget_cap": 0},
    }
    cp = run(
        "marketplace-safety-gate",
        "--quote",
        str(quote),
        "--action-json",
        json.dumps(risky),
        "--extra-text",
        "requires SECRET_TOKEN and wallet checkout",
        "--no-write",
        "--json",
    )
    assert cp.returncode == 1
    payload = json.loads(cp.stdout)
    reasons = set(payload["decision"]["blocked_reasons"])
    assert payload["status"] == "blocked_fail_closed"
    assert "payment_required" in reasons
    assert "over_budget" in reasons
    assert "secret_or_credential_access" in reasons
    assert "public_publish" in reasons
    assert "deploy_or_production_mutation" in reasons
    assert "external_message_or_post" in reasons
    assert payload["decision"]["payment_allowed"] is False
