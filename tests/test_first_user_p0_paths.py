import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
CLI = (sys.executable, str(REPO / "scripts" / "agentpress.py"))


def run(*args, cwd=REPO):
    return subprocess.run((*CLI, *args), cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_doctor_json_has_machine_readable_next_steps_for_sparse_repo(tmp_path):
    proc = run("doctor", str(tmp_path), "--mode", "local", "--json")
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["status"] == "fail"
    assert payload["next_steps"]
    assert payload["recommendations"]
    commands = "\n".join(step["command"] for step in payload["next_steps"])
    assert "llms-init" in commands
    assert "first-run-wizard" in commands


def test_start_is_concise_json_first_user_path():
    proc = run("start", "--json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert [c["name"] for c in payload["commands"]] == ["doctor", "llms-init", "first-run-wizard"]
    assert payload["ranked_first_actions"][0]["id"] == "doctor"
    assert payload["version_channel"]["channel"] in {"release_candidate", "stable_or_local"}
    assert payload["safety"]["external_writes"] is False


def test_llms_init_creates_minimal_surfaces(tmp_path):
    proc = run("llms-init", str(tmp_path), "--title", "Demo", "--json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert sorted(payload["written"]) == [".well-known/agentpress.json", "llms.txt"]
    assert (tmp_path / "llms.txt").exists()
    manifest = json.loads((tmp_path / ".well-known" / "agentpress.json").read_text())
    assert manifest["commands"]["doctor"] == "agentpress doctor . --json"


def test_node_shim_start_fast_path_does_not_require_python():
    proc = subprocess.run(("node", str(REPO / "bin" / "agentpress.js"), "start", "--json"), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["schema_version"].startswith("2026-05-05.agentpress-node-fast-start.")
    assert payload["commands"][1]["name"] == "llms-init"
    assert payload["ranked_first_actions"][0]["id"] == "doctor"
    assert payload["version_channel"]["channel"] in {"release_candidate", "stable_or_local"}


def test_node_shim_doctor_no_python_returns_actionable_json():
    proc = subprocess.run(
        ("node", str(REPO / "bin" / "agentpress.js"), "doctor", "--json"),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHON": "/definitely/missing/python"},
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["mode"] == "node-fast-path"
    assert payload["next_steps"]
    assert payload["entrypoints"]
    assert payload["version_channel"]["stable_latest"]["status"] == "not_asserted_without_registry_check"
