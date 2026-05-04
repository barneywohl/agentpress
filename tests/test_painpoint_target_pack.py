"""
Tests for painpoint-target-pack command.

Covers:
  - Correct candidate selection and match scoring
  - low_confidence_match finding when fallback (score==0) fires
  - Secret regex coverage: OpenAI, GitHub PAT, AWS, JWT, Slack tokens
  - No-secret inputs pass clean
  - approval_required gate always present in output

Run: pytest tests/test_painpoint_target_pack.py -v
"""
import argparse
import importlib.util
import json
import pathlib

import pytest

_SCRIPTS = pathlib.Path(__file__).parent.parent / "scripts"
_SPEC = importlib.util.spec_from_file_location("agentpress", _SCRIPTS / "agentpress.py")
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

painpoint_target_pack = _MOD.painpoint_target_pack


def _ns(**kwargs) -> argparse.Namespace:
    base = {
        "base_url": "https://example.com/agentpress/",
        "no_write": True,
        "json": True,
        "strict": False,
        "issue_url": "",
        "painpoint": "",
        "host": "unknown_host",
        "provider": "unknown_provider",
        "tool": "unknown_tool",
        "error": "",
        "out": "/tmp/ptp-test.json",
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


class TestCandidateSelection:
    def test_mcp_terms_match_mcp_config_guard(self, capsys):
        rc = painpoint_target_pack(_ns(
            issue_url="https://github.com/cline/cline/issues/10499",
            painpoint="MCP config mutation backup restore",
            host="cline",
            provider="mcp",
            tool="mcp_server",
        ))
        data = json.loads(capsys.readouterr().out)
        assert data["matched_solution"]["id"] == "mcp_config_mutation_guard"
        assert rc == 0

    def test_provider_adapter_terms_select_adapter_pack(self, capsys):
        rc = painpoint_target_pack(_ns(
            issue_url="https://github.com/cline/cline/issues/10336",
            painpoint="provider tool vocabulary mismatch execute_command invalid_arguments",
            host="cline",
            provider="claude_code",
            tool="execute_command",
        ))
        data = json.loads(capsys.readouterr().out)
        assert data["matched_solution"]["id"] == "provider_adapter_repro_pack"

    def test_best_score_gt0_produces_ready_status(self, capsys):
        painpoint_target_pack(_ns(
            issue_url="https://github.com/cline/cline/issues/10499",
            painpoint="mcp config server",
        ))
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "ready_for_manual_approval"


class TestLowConfidenceFallback:
    """Bug: score==0 silently falls back to candidates[2] with no finding.

    After fix: a low_confidence_match finding must be present when no
    candidate scored > 0, and the status should reflect degraded confidence.
    """

    def test_zero_score_emits_low_confidence_finding(self, capsys):
        """FAILS before fix: no finding when fallback fires."""
        painpoint_target_pack(_ns(
            issue_url="https://github.com/cline/cline/issues/99999",
            painpoint="completely unrelated topic",
            host="unknown_host",
            provider="unknown_provider",
            tool="unknown_tool",
        ))
        data = json.loads(capsys.readouterr().out)
        finding_msgs = [f["message"] for f in data.get("findings", [])]
        # After fix this assertion must pass; before fix it fails.
        assert any("low_confidence" in m or "fallback" in m for m in finding_msgs), (
            "Expected a low_confidence_match finding when score==0 fallback fires"
        )

    def test_zero_score_status_is_low_confidence_not_ready(self, capsys):
        """FAILS before fix: status is ready_for_manual_approval even with no match."""
        painpoint_target_pack(_ns(
            issue_url="https://github.com/cline/cline/issues/99999",
            painpoint="completely unrelated topic",
        ))
        data = json.loads(capsys.readouterr().out)
        # After fix: must NOT be ready_for_manual_approval when score==0
        assert data["status"] != "ready_for_manual_approval", (
            "Low-confidence fallback should downgrade status"
        )


class TestSecretRegex:
    """Bug: regex misses JWT, AWS, Slack, and high-entropy bearer tokens."""

    def test_openai_key_blocked(self, capsys):
        painpoint_target_pack(_ns(
            painpoint="sk-proj-abc123DEFGH456ijklMNOP789",
        ))
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "blocked_redact"

    def test_github_pat_blocked(self, capsys):
        painpoint_target_pack(_ns(
            painpoint="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345",
        ))
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "blocked_redact"

    def test_aws_key_blocked(self, capsys):
        """FAILS before fix: AWS AKIA keys not covered by current regex."""
        painpoint_target_pack(_ns(
            painpoint="AKIAIOSFODNN7EXAMPLE",
        ))
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "blocked_redact", (
            "AWS AKIA key should be detected by secret regex"
        )

    def test_jwt_blocked(self, capsys):
        """FAILS before fix: JWT tokens not covered by current regex."""
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        painpoint_target_pack(_ns(painpoint=jwt))
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "blocked_redact", (
            "JWT token (eyJ…) should be detected by secret regex"
        )

    def test_slack_token_blocked(self, capsys):
        """FAILS before fix: Slack bot tokens not covered by current regex."""
        painpoint_target_pack(_ns(
            painpoint=("xo" + "xb-" + "123456789012-1234567890123-" + "abcdefghijklmnopqrstuvwx"),
        ))
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "blocked_redact", (
            "Slack bot token should be detected by secret regex"
        )

    def test_clean_painpoint_passes(self, capsys):
        painpoint_target_pack(_ns(
            issue_url="https://github.com/cline/cline/issues/10499",
            painpoint="MCP config backup restore approval",
            host="cline",
            provider="mcp",
            tool="mcp_server",
        ))
        data = json.loads(capsys.readouterr().out)
        assert data["status"] != "blocked_redact"


class TestApprovalGate:
    def test_approval_required_always_true(self, capsys):
        painpoint_target_pack(_ns(
            issue_url="https://github.com/cline/cline/issues/10499",
            painpoint="mcp config",
        ))
        data = json.loads(capsys.readouterr().out)
        assert data["manual_outreach_draft"]["approval_required"] is True

    def test_acceptance_gates_include_manual_approval(self, capsys):
        painpoint_target_pack(_ns(
            issue_url="https://github.com/cline/cline/issues/10499",
            painpoint="mcp config",
        ))
        data = json.loads(capsys.readouterr().out)
        assert "manual approval before posting" in data["acceptance_gates"]
