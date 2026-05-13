"""Tests for agentpress_core mirror the @agentpress/core TypeScript suite."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentpress_core import (
    SPEC_VERSION,
    check_rate_limit,
    is_action_allowed,
    parse,
    validate,
)

FIXTURE = """# agents.txt v1.0
[meta]
spec_version = 1.0
project = test-project
maintainer = jane@example.com
contact_for_agents = bot-relations@example.com
last_updated = 2026-05-13
license = MIT
ai_disclosure_required = true

[allowed_actions]
read_documentation
read_source_code
file_pull_request

[prohibited_actions]
merge_to_main
exfiltrate_secrets

[requires_human_approval]
schema_migrations
changes_touching = payments/**, billing/**

[entry_points]
agent_guide = /AGENTS.md
test_command = npm test

[mcp]
server = https://example.com/mcp
auth = oauth2
capabilities = search_docs, run_tests, draft_pr

[verification]
ci_runner = github_actions
required_checks = lint, test
expected_exit = 0

[rate_limits]
max_pull_requests_per_day = 5
max_issues_per_day = 10

[scope]
max_files_changed = 25
max_lines_changed = 800
single_purpose_pr = true

[disclosure]
pr_label = agent-authored
commit_trailer = Authored-by-Agent: <agent-name>
require_attribution_in_pr_body = true

[contact]
escalation = https://example.com/help

[fyi]
preferred_branch_naming = agent/<purpose>
"""


def test_parse_meta():
    data = parse(FIXTURE)
    assert data.meta.spec_version == "1.0"
    assert data.meta.project == "test-project"
    assert data.meta.maintainer == "jane@example.com"
    assert data.meta.ai_disclosure_required is True


def test_parse_allowed_actions():
    data = parse(FIXTURE)
    assert data.allowed_actions == ["read_documentation", "read_source_code", "file_pull_request"]


def test_parse_prohibited_actions():
    data = parse(FIXTURE)
    assert data.prohibited_actions == ["merge_to_main", "exfiltrate_secrets"]


def test_parse_requires_human_approval_mixed():
    data = parse(FIXTURE)
    assert data.requires_human_approval["schema_migrations"] is True
    assert data.requires_human_approval["changes_touching"] == ["payments/**", "billing/**"]


def test_parse_mcp_section():
    data = parse(FIXTURE)
    assert data.mcp is not None
    assert data.mcp.server == "https://example.com/mcp"
    assert data.mcp.auth == "oauth2"
    assert data.mcp.capabilities == ["search_docs", "run_tests", "draft_pr"]


def test_parse_rate_limits():
    data = parse(FIXTURE)
    assert data.rate_limits.max_pull_requests_per_day == 5
    assert data.rate_limits.max_issues_per_day == 10


def test_parse_scope_bool():
    data = parse(FIXTURE)
    assert data.scope.single_purpose_pr is True


def test_validate_well_formed_ok():
    result = validate(parse(FIXTURE))
    assert result.ok is True
    assert all(i.severity != "error" for i in result.issues)


def test_validate_missing_required_errors():
    result = validate(parse("[meta]\nspec_version = 1.0\n"))
    assert result.ok is False
    keys = {i.key for i in result.issues if i.severity == "error"}
    assert "project" in keys
    assert "maintainer" in keys


def test_validate_unknown_spec_version_warns():
    future = FIXTURE.replace("spec_version = 1.0", "spec_version = 9.9")
    result = validate(parse(future))
    assert result.ok is True
    assert any(
        i.severity == "warning" and i.key == "spec_version" for i in result.issues
    )


def test_is_action_allowed_deny():
    data = parse(FIXTURE)
    assert is_action_allowed(data, "merge_to_main") == "deny"


def test_is_action_allowed_requires_approval():
    data = parse(FIXTURE)
    assert is_action_allowed(data, "schema_migrations") == "requires_approval"


def test_is_action_allowed_allow():
    data = parse(FIXTURE)
    assert is_action_allowed(data, "read_documentation") == "allow"


def test_is_action_allowed_unknown():
    data = parse(FIXTURE)
    assert is_action_allowed(data, "send_email_blast") == "unknown"


def test_is_action_allowed_case_insensitive():
    data = parse(FIXTURE)
    assert is_action_allowed(data, "MERGE_TO_MAIN") == "deny"


def test_check_rate_limit_under():
    data = parse(FIXTURE)
    assert check_rate_limit(data, "pr", 4) is True


def test_check_rate_limit_at_limit():
    data = parse(FIXTURE)
    assert check_rate_limit(data, "pr", 5) is False


def test_check_rate_limit_no_limit_set():
    data = parse(FIXTURE)
    assert check_rate_limit(data, "branch", 99) is True


def test_parse_tolerates_crlf():
    data = parse(FIXTURE.replace("\n", "\r\n"))
    assert data.meta.project == "test-project"


def test_parse_tolerates_noise():
    noisy = (
        "\n\n   # comment\n[meta]\n  spec_version  =  1.0  \n  project = noisy\n"
        "  maintainer = a@b\n[allowed_actions]\n  read_documentation  \n"
        "[prohibited_actions]\n  merge_to_main\n[requires_human_approval]\n"
        "[entry_points]\n[disclosure]\n  pr_label = agent\n"
    )
    data = parse(noisy)
    assert data.meta.spec_version == "1.0"
    assert data.allowed_actions == ["read_documentation"]


def test_spec_version_constant():
    assert SPEC_VERSION == "1.0"


def test_unknown_sections_preserved():
    future = FIXTURE + "\n[experimental_v2_thing]\nfoo = bar\n"
    data = parse(future)
    assert data.unknown_sections["experimental_v2_thing"]["foo"] == "bar"
