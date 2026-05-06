import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, str(ROOT / "scripts" / "agentpress.py")]


def run(*args):
    return subprocess.run(CLI + list(args), cwd=ROOT, text=True, capture_output=True, check=True)


def test_material_kit_creates_agent_readable_public_painpoint_fixture(tmp_path):
    out = tmp_path / "material-kits"
    cp = run(
        "material-kit",
        "--target-url", "https://github.com/OpenHands/OpenHands/issues/12316",
        "--ecosystem", "OpenHands",
        "--painpoint", "plugin marketplace metadata needs repo-native proof",
        "--artifact", "agentpress/growth/gorilla-utility-pack/approval-packets/1-openhands-openhands-runtime-hang.json",
        "--command", "python3 scripts/agentpress.py discovery-bridge queue --json",
        "--out", str(out),
        "--json",
    )
    payload = json.loads(cp.stdout)
    kit = Path(payload["out"])

    assert payload["status"] == "ok"
    assert (kit / "llms.txt").exists()
    assert (kit / "RUN_THIS.md").exists()
    manifest = json.loads((kit / "material-manifest.json").read_text(encoding="utf-8"))
    receipt = json.loads((kit / "proof-receipt.json").read_text(encoding="utf-8"))

    assert manifest["schema_version"].endswith("agentpress-material-kit.v1")
    assert manifest["ecosystem"] == "OpenHands"
    assert manifest["target_url"].startswith("https://github.com/OpenHands")
    assert manifest["safety"]["external_posting"] is False
    assert manifest["safety"]["requires_human_approval_before_commenting"] is True
    assert "discovery-bridge queue" in manifest["utility_command"]
    assert receipt["status"] == "prepared_not_posted"
    assert receipt["external_effects"] == []
    assert "No external comments" in (kit / "llms.txt").read_text(encoding="utf-8")
