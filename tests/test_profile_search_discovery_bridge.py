import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, str(ROOT / "scripts" / "agentpress.py")]


def run(*args):
    return subprocess.run(CLI + list(args), cwd=ROOT, text=True, capture_output=True, check=True)


def test_discovery_bridge_unifies_profiles_packs_marketplace_and_queue(tmp_path):
    out = tmp_path / "bridge.json"
    cp = run("discovery-bridge", "queue", "--out", str(out), "--json")
    payload = json.loads(cp.stdout)
    written = json.loads(out.read_text(encoding="utf-8"))

    assert payload["schema_version"].endswith("profile-search-discovery-bridge.v1")
    assert payload == written
    for kind in ["agent_profile", "profile_capability", "utility_pack", "marketplace_service", "execution_queue", "execution_queue_item", "queue_adapter"]:
        assert payload["counts_by_kind"].get(kind, 0) >= 1
    assert any(r["kind"] == "execution_queue" and r["status"] == "prepared_not_posted" for r in payload["results"])
    assert any(r["kind"] == "execution_queue_item" and r["approval_required"] is True for r in payload["results"])
    assert "human approval" in payload["safety"].lower()


def test_search_index_includes_bridge_marketplace_utility_and_queue_records(tmp_path):
    index = tmp_path / "search-index.json"
    run("index-search", "--out", str(index), "--json")
    idx = json.loads(index.read_text(encoding="utf-8"))
    kinds = {r["kind"] for r in idx["records"]}

    assert {"utility_pack", "marketplace_service", "execution_queue", "queue_adapter"}.issubset(kinds)

    queue = json.loads(run("search", "prepared_not_posted queue", "--index", str(index), "--json").stdout)
    market = json.loads(run("search", "marketplace agent_onboard", "--index", str(index), "--json").stdout)
    pack = json.loads(run("search", "gorilla utility cline", "--index", str(index), "--json").stdout)

    assert any(r["kind"] == "execution_queue" for r in queue["results"])
    assert any(r["kind"] == "marketplace_service" and "service_id" in r for r in market["results"])
    assert any(r["kind"] == "utility_pack" and "pack_id" in r for r in pack["results"])
