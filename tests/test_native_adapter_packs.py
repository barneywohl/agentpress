import json
import pathlib

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
