import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, str(ROOT / "scripts" / "agentpress.py")]


def run(*args):
    return subprocess.run(CLI + list(args), cwd=ROOT, text=True, capture_output=True, check=True)


def test_gorilla_approval_packets_are_exact_and_fail_closed(tmp_path):
    out = tmp_path / "approval-packets"
    cp = run("gorilla-approval-packets", "--out", str(out), "--limit", "5", "--json")
    payload = json.loads(cp.stdout)
    written = json.loads((out / "index.json").read_text(encoding="utf-8"))

    assert payload == written
    assert payload["schema_version"].endswith("approval-packet-index.v1")
    assert payload["status"] == "prepared_not_posted"
    assert payload["packet_count"] == 5
    assert "No external post" in payload["hard_gate"]

    packets = sorted(out.glob("*.json"))
    assert len(packets) == 6  # index + 5 packets
    packet_payloads = [json.loads(p.read_text(encoding="utf-8")) for p in packets if p.name != "index.json"]
    assert any(p["ecosystem"] == "OpenHands" and p["status"] == "ready_for_exact_human_approval" for p in packet_payloads)
    assert any(p["ecosystem"] == "Cline" and p["status"] == "hold_security_sensitive" for p in packet_payloads)
    for packet in packet_payloads:
        assert packet["target_url"].startswith("https://github.com/")
        assert packet["draft"]
        if packet["status"] == "ready_for_exact_human_approval":
            assert "explicit_human_approval_of_exact_target_and_draft" in packet["required_controls"]
        else:
            assert "do_not_post" in packet["required_controls"]
        assert "do not automate external posting" in packet["do_not"]
