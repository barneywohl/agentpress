import json
import subprocess
import sys


def run_cli(*args):
    return subprocess.run([sys.executable, "scripts/agentpress.py", *args], text=True, capture_output=True)


def test_gorilla_utility_pack_generates_target_packs(tmp_path):
    out = tmp_path / "gorilla"
    cp = run_cli("gorilla-utility-pack", "--out", str(out), "--json")
    assert cp.returncode == 0
    payload = json.loads(cp.stdout)
    assert payload["schema_version"] == "2026-05-05.agentpress-gorilla-utility-pack.v1"
    assert payload["status"] == "ready_not_sent"
    assert payload["target_count"] >= 5
    assert "Human approval required" in payload["external_execution_gate"]
    assert (out / "manifest.json").exists()
    for target in payload["targets"]:
        pack = out / f"{target['id']}.json"
        assert pack.exists()
        data = json.loads(pack.read_text())
        assert data["status"] == "ready_not_sent"
        assert any("not marketing" in rule for rule in data["rules"])
        assert "external-proof-intake" in " ".join(data["proof_loop"])


def test_gorilla_utility_pack_no_write(tmp_path):
    out = tmp_path / "gorilla"
    cp = run_cli("gorilla-utility-pack", "--out", str(out), "--no-write", "--json")
    assert cp.returncode == 0
    assert not out.exists()
    payload = json.loads(cp.stdout)
    assert payload["target_count"] >= 5
