import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, str(ROOT / "scripts" / "agentpress.py")]


def run(*args):
    return subprocess.run(CLI + list(args), cwd=ROOT, text=True, capture_output=True, check=True)


def test_message_route_returns_profile_fields(tmp_path):
    directory = tmp_path / "capability-index.json"
    directory.write_text(json.dumps({
        "capabilities": {"validate_agentpress_bundle": ["agent-a"]},
        "agents": {
            "agent-a": {
                "display_name": "Agent A",
                "capabilities": ["validate_agentpress_bundle"],
                "profile_card": "agentpress/identity/agent-a.json",
                "contact": "agent-comms/agents/agent-a/inbox",
                "trust_tier": "reference",
            }
        },
    }) + "\n")
    cp = run("message", "route", "--capability", "validate_agentpress_bundle", "--directory", str(directory), "--json")
    payload = json.loads(cp.stdout)
    assert payload["status"] == "ok"
    assert "profile_card" in payload["profile_fields"]
    assert payload["agents"][0]["display_name"] == "Agent A"
    assert payload["agents"][0]["trust_tier"] == "reference"


def test_marketplace_trust_scores_nested_pricing_and_trust(tmp_path):
    root = tmp_path
    market = root / "agentpress" / "marketplace" / "marketplace-index.json"
    market.parent.mkdir(parents=True)
    market.write_text(json.dumps({
        "services": [{
            "service_id": "svc-free",
            "title": "Free trusted service",
            "command": "agentpress example",
            "capabilities": ["search"],
            "pricing": {"payment_required": False},
            "trust": {"evidence": ["receipt.json"]},
        }]
    }) + "\n")
    cp = run("marketplace-trust", str(root), "--marketplace", "agentpress/marketplace/marketplace-index.json", "--out", str(tmp_path / "trust.json"), "--json")
    payload = json.loads(cp.stdout)
    svc = payload["services"][0]
    assert svc["signals"]["free_first"] is True
    assert svc["signals"]["has_trust_evidence"] is True
    assert svc["tier"] == "high"
