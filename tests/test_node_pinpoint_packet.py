import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_CLI = ["node", str(ROOT / "bin" / "agentpress.js")]


def test_pinpoint_packet_reports_missing_surfaces_without_python(tmp_path):
    cp = subprocess.run(
        NODE_CLI + ["pinpoint-packet", str(tmp_path), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(cp.stdout)
    assert payload["schema_version"] == "2026-05-06.agentpress-pinpoint-packet.v1"
    assert payload["status"] == "needs_action"
    assert "missing_agent_readme_surface: llms.txt" in payload["blockers"]
    assert payload["safety"]["external_writes"] is False
    assert any(step["command"].startswith("agentpress llms-init") for step in payload["next_steps"])


def test_pinpoint_packet_writes_evidence_when_requested(tmp_path):
    (tmp_path / "llms.txt").write_text("# demo\n")
    wk = tmp_path / ".well-known"
    wk.mkdir()
    (wk / "agentpress.json").write_text(json.dumps({"schema_version": "test"}) + "\n")
    out = tmp_path / "packet.json"
    cp = subprocess.run(
        NODE_CLI + ["pinpoint-packet", str(tmp_path), "--out", str(out), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(cp.stdout)
    written = json.loads(out.read_text())
    assert payload["status"] == "ok"
    assert written["status"] == "ok"
    assert payload["written"] == str(out)
