import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent.parent
NATIVE = ROOT / "agentpress" / "adapters" / "native"

REQUIRED_TARGETS = ["cline", "roo", "openhands", "mcp"]
REQUIRED_README_TERMS = [
    "Proof command",
    "Safety policy",
    "Common remediation",
    "landing-receipt",
    "submission-pack",
]


def test_native_adapter_manifest_points_to_priority_packs():
    manifest = json.loads((NATIVE / "manifest.json").read_text())
    targets = {t["target"]: t for t in manifest["targets"]}

    for target in REQUIRED_TARGETS:
        assert target in targets
        assert targets[target]["readme"].endswith(f"/{target}/README.md")
        assert targets[target]["config"].startswith("https://barneywohl.github.io/agentpress/")


def test_priority_native_adapter_readmes_are_actionable():
    for target in REQUIRED_TARGETS:
        text = (NATIVE / target / "README.md").read_text()
        for term in REQUIRED_README_TERMS:
            assert term in text, f"{target} missing {term}"
        assert "Do not claim" in text or "do not claim" in text


def test_priority_native_adapter_configs_have_smoke_commands_and_safety():
    for target in REQUIRED_TARGETS:
        config_files = list((NATIVE / target).glob("*-agentpress*.json"))
        assert config_files, target
        config = json.loads(config_files[0].read_text())
        assert config["target"] == target
        assert config["smoke_commands"]
        assert "approval" in config["safety"].lower()
        assert config["proof_receipt_example"].endswith(f"/{target}/proof-receipt.example.json")
        assert config["host_transcript_template"].endswith(f"/{target}/host-transcript.template.json")
        assert config["proof_receipt_required_fields"] == [
            "agent_id", "runtime", "service_id", "capability_id", "commands_run", "artifacts", "result_status", "redaction_attestation"
        ]


def run_cli(*args):
    return subprocess.run([sys.executable, "scripts/agentpress.py", *args], cwd=ROOT, text=True, capture_output=True)


def test_priority_native_adapter_proof_receipts_and_transcripts_validate():
    for target in REQUIRED_TARGETS:
        proof_path = NATIVE / target / "proof-receipt.example.json"
        transcript_path = NATIVE / target / "host-transcript.template.json"

        proof = run_cli("proof-receipt-verify", str(proof_path), "--json")
        assert proof.returncode == 0, proof.stdout + proof.stderr
        proof_data = json.loads(proof.stdout)
        assert proof_data["runtime"] == target
        assert proof_data["service_id"] == "agentpress-native-adapter"

        transcript = run_cli("host-transcript-validate", str(transcript_path), "--no-write", "--json")
        assert transcript.returncode == 0, transcript.stdout + transcript.stderr
        transcript_data = json.loads(transcript.stdout)
        assert transcript_data["host"] == target
        assert transcript_data["command_count"] >= 1


def test_native_adapter_check_requires_priority_proof_surfaces():
    cp = run_cli("native-adapter-check", "agentpress/adapters/native", "--json")
    assert cp.returncode == 0, cp.stdout + cp.stderr
    payload = json.loads(cp.stdout)
    priority = {row["target"]: row for row in payload["targets"] if row["target"] in REQUIRED_TARGETS}
    assert set(priority) == set(REQUIRED_TARGETS)
    assert all(row["status"] == "pass" for row in priority.values())
