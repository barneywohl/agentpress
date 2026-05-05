import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, str(ROOT / "scripts" / "agentpress.py")]


def run(*args):
    return subprocess.run(CLI + list(args), cwd=ROOT, text=True, capture_output=True, check=True)


def test_agent_profile_registry_exposes_capabilities_and_cards(tmp_path):
    out = tmp_path / "agent-profile-registry.json"
    cp = run("agent-profile-registry", "--out", str(out), "--json")
    summary = json.loads(cp.stdout)
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert summary["profile_count"] >= 1
    assert payload["generated_by"] == "agentpress agent-profile-registry"
    assert "verify_source_map" in payload["capabilities"]
    profile = next(p for p in payload["profiles"] if p["agent_id"] == "agentpress-reference-agent")
    assert profile["profile_card"].endswith("agentpress/profiles/agentpress-reference-agent/agent-profile.json")
    assert profile["can_receive_tasks"] is True
    assert "profile_card" in payload["profile_fields"]


def test_profile_registry_and_search_are_deterministic(tmp_path):
    reg = tmp_path / "registry.json"
    idx = tmp_path / "search.json"

    run("agent-profile-registry", "--out", str(reg), "--json")
    first_registry = reg.read_text(encoding="utf-8")
    run("agent-profile-registry", "--out", str(reg), "--json")
    second_registry = reg.read_text(encoding="utf-8")
    run("index-search", "--out", str(idx), "--json")
    first_index = idx.read_text(encoding="utf-8")
    run("index-search", "--out", str(idx), "--json")
    second_index = idx.read_text(encoding="utf-8")

    assert first_registry == second_registry
    assert first_index == second_index


def test_search_returns_profile_capability_hit_with_profile_card(tmp_path):
    index = tmp_path / "search-index.json"
    run("index-search", "--out", str(index), "--json")
    cp = run("search", "verify_source_map", "--index", str(index), "--json")
    payload = json.loads(cp.stdout)

    assert payload["status"] == "ok"
    hit = next(r for r in payload["results"] if r["kind"] == "profile_capability")
    assert hit["capability"] == "verify_source_map"
    assert hit["profile_card"].endswith("agentpress/profiles/agentpress-reference-agent/agent-profile.json")
