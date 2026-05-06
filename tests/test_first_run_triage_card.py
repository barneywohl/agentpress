import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "agentpress" / "first-run" / "first-run-triage-card.json"
PAGE = ROOT / "agentpress" / "first-run" / "index.html"


def test_first_run_triage_card_is_safe_and_actionable():
    payload = json.loads(CARD.read_text())
    assert payload["schema_version"] == "2026-05-06.agentpress-first-run-triage-card.v1"
    assert payload["status"] == "ready_static"
    assert payload["privacy_boundary"]["external_effects"] == []
    assert payload["privacy_boundary"]["posts_without_human_approval"] is False
    assert len(payload["triage_steps"]) >= 4
    runs = "\n".join(step["run"] for step in payload["triage_steps"])
    assert "start --json" in runs
    assert "doctor . --mode self-check --json" in runs
    assert "Do not post" in runs
    assert any("Registry/latest-vs-rc" in mode["symptom"] for mode in payload["known_failure_modes"])
    assert PAGE.exists()
    assert "first-run-triage-card.json" in PAGE.read_text()
