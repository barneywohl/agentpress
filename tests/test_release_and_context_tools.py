import importlib.util
import json
import pathlib
import subprocess

_ROOT = pathlib.Path(__file__).parent.parent
_SCRIPT = _ROOT / "scripts" / "agentpress.py"


def run_cmd(*args):
    return subprocess.run(["python3", str(_SCRIPT), *args], cwd=_ROOT, text=True, capture_output=True, check=False)


def test_release_promote_checklist_blocks_without_external_proof_no_network(tmp_path):
    out = tmp_path / "promote.json"
    res = run_cmd("release-promote-checklist", ".", "--no-network", "--out", str(out), "--json")
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["status"] == "blocked"
    checks = {c["name"]: c for c in data["checks"]}
    assert "independent_external_proof" in checks
    assert checks["independent_external_proof"]["status"] == "blocked"
    assert data["promotion_allowed"] is False


def test_context_package_init_writes_focused_root(tmp_path):
    out_dir = tmp_path / "handoff-root"
    res = run_cmd("context-package-init", ".", "--out", str(out_dir), "--max-files", "12", "--json")
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["status"] == "ok"
    assert (out_dir / "source-map.json").exists()
    assert (out_dir / "freshness.json").exists()
    assert (out_dir / "TASK_CARD.md").exists()
    sm = json.loads((out_dir / "source-map.json").read_text())
    assert sm["selected_count"] <= 12


def test_handoff_root_pick_alias(tmp_path):
    out_dir = tmp_path / "pick"
    res = run_cmd("handoff-root-pick", ".", "--out", str(out_dir), "--max-files", "5", "--json")
    assert res.returncode == 0
    assert json.loads(res.stdout)["selected_count"] <= 5
