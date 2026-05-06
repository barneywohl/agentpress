import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "agentpress.py"


def run_cli(*args, cwd=ROOT):
    return subprocess.run([sys.executable, str(CLI), *args], cwd=cwd, check=True, text=True, capture_output=True)


def test_material_growth_loop_index_aggregates_kits(tmp_path):
    run_cli(
        "material-kit",
        str(tmp_path),
        "--slug",
        "mcp-404-rescue",
        "--ecosystem",
        "mcp",
        "--painpoint",
        "server setup docs return an ambiguous 404 for agents",
        "--target-url",
        "https://example.test/mcp/issues/404",
        "--command",
        "python3 scripts/agentpress.py provider-error-explainer --error '404' --json",
        "--json",
    )
    result = run_cli("material-growth-loop-index", str(tmp_path), "--json")
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["kit_count"] == 1

    index = json.loads((tmp_path / "agentpress/growth/material-loop/material-growth-loop-index.json").read_text())
    assert index["schema_version"] == "2026-05-06.agentpress-material-growth-loop-index.v1"
    assert index["kit_count"] == 1
    assert index["kits"][0]["slug"] == "mcp-404-rescue"
    assert index["kits"][0]["safe_for_public_contact"] is False
    assert index["safety"]["public_contact_requires_exact_human_approval"] is True
    assert (tmp_path / "agentpress/growth/material-loop/index.html").exists()
