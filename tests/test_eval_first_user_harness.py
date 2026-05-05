import json
import pathlib
import tempfile

from scripts import eval_first_user_harness as harness


def test_create_scenarios_are_under_requested_tmp_root():
    with tempfile.TemporaryDirectory(prefix="agentpress-harness-test-", dir="/tmp") as tmp:
        root = pathlib.Path(tmp)
        for name in harness.DEFAULT_SCENARIOS:
            repo = harness.create_scenario(root, name)
            assert repo.exists()
            assert root in repo.parents
        assert (root / "js-app" / "package.json").exists()
        assert (root / "python-package" / "pyproject.toml").exists()


def test_assess_actionability_detects_machine_readable_errors():
    payload = {"status": "fail", "errors": ["missing README.md"], "entrypoints": []}
    assert harness.assess_actionability(json.dumps(payload), payload)


def test_harness_smoke_writes_report_and_cleans_generated_repos(tmp_path):
    status = tmp_path / "status.md"
    rc = harness.main([
        "--scenario", "empty-repo",
        "--status-out", str(status),
        "--json",
        "--timeout", "20",
    ])
    assert rc == 0
    text = status.read_text(encoding="utf-8")
    assert "AgentPress Karpathy Mini First-User Eval Harness" in text
    assert "empty-repo" in text
    assert "cleaned: `True`" in text
