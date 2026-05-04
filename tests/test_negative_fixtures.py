"""AP-012: Adversarial bundle validation — verify fails closed for broken contracts.

Acceptance gate: `verify` must return non-zero for every fixture in this suite.
Covers all existing broken-bundle fixtures plus programmatically constructed cases.

Run: pytest tests/test_negative_fixtures.py -v
"""
import argparse
import importlib.util
import json
import pathlib
import shutil

import pytest

# ---------------------------------------------------------------------------
# Module import
# ---------------------------------------------------------------------------
_SCRIPTS = pathlib.Path(__file__).parent.parent / "scripts"
_SPEC = importlib.util.spec_from_file_location("agentpress", _SCRIPTS / "agentpress.py")
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

audit_root = _MOD.audit_root
verify = _MOD.verify
negative_fixtures = _MOD.negative_fixtures

_BROKEN_BUNDLES = pathlib.Path(__file__).parent.parent / "agentpress" / "fixtures" / "broken-bundles"
_NEGATIVE_MANIFEST = _BROKEN_BUNDLES / "expected-failures.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_VALID_BUNDLE_FILES = {
    "README.md": "# Test\n",
    "AGENT_ENTRYPOINT.md": (
        "# Entrypoint\n\n"
        "Primary task: test\n\n"
        "Input contract: none\n\n"
        "Expected output schema: none\n\n"
        "allowed-actions: read\n"
    ),
    "disclaimer.md": "allowed-actions boundary applies.\n",
    "citation-policy.md": "Cite sources. allowed-actions apply.\n",
    "agent-task-card.json": json.dumps({
        "schema_version": "2026-05-03.agentpress-task-card.v1",
        "title": "Adversarial test card",
        "task_type": "research",
        "target_agents": ["claude"],
        "objective": "Adversarial test",
        "input_contract": {"required": []},
        "output_contract": {"required": []},
        "allowed_actions": ["read"],
        "prohibited_actions": [],
        "scoring_rubric": {"pass": "Bundle validates and preserves safety boundaries."},
        "disclaimer": "Generated test bundle; allowed-actions boundary applies.",
    }),
    "source-map.json": json.dumps({
        "schema_version": "2026-05-03.agentpress-source-map.v1",
        "publication": "Test",
        "claims": [{
            "claim_id": "C001",
            "claim": "test claim",
            "confidence": "high",
            "sources": [{"title": "test", "url_or_path": "README.md"}],
        }],
    }),
    "freshness.json": json.dumps({
        "schema_version": "2026-05-03.agentpress-freshness.v1",
        "publication": "Test",
        "generated_at": "2026-05-04T00:00:00Z",
        "refresh_policy": "on change",
        "default_freshness_window_days": 7,
    }),
    "allowed-actions.json": json.dumps({
        "schema_version": "2026-05-03.agentpress-allowed-actions.v1",
        "allowed": ["read"],
        "requires_human_approval": [],
        "prohibited": [],
    }),
    "llms.txt": "# AgentPress test\n",
    "sitemap.xml": '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
    "CITATION.cff": "cff-version: 1.2.0\ntitle: Test\nversion: 0.1.0\n",
    ".well-known/ai-ingestion.json": json.dumps({
        "schema_version": "2026-05-03.agentpress-ai-ingestion.v1",
        "name": "Test",
        "canonical_url": "https://example.com/",
        "entrypoint": "AGENT_ENTRYPOINT.md",
        "llms_txt": "llms.txt",
        "task_card": "agent-task-card.json",
        "source_map": "source-map.json",
        "allowed_actions": "allowed-actions.json",
        "citation_policy": "citation-policy.md",
        "disclaimer": "disclaimer.md",
    }),
}


def _make_valid_bundle(root: pathlib.Path) -> pathlib.Path:
    """Write a minimal passing bundle into root/bundle/."""
    bd = root / "bundle"
    bd.mkdir(parents=True, exist_ok=True)
    (bd / ".well-known").mkdir(exist_ok=True)
    for rel, content in _MINIMAL_VALID_BUNDLE_FILES.items():
        p = bd / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return bd


def _verify_args(bundle_path: pathlib.Path) -> argparse.Namespace:
    return argparse.Namespace(
        out=str(bundle_path),
        json=True,
        strict_schema=False,
    )


# ---------------------------------------------------------------------------
# AP-012 — existing broken-bundle fixtures must fail verify
# ---------------------------------------------------------------------------

class TestExistingBrokenBundlesFailClosed:
    """Every broken-bundle fixture must cause verify to return non-zero."""

    @pytest.mark.parametrize("fixture_name", [
        "missing-allowed-actions",
        "bad-task-card-type",
        "source-map-missing-claims",
        "freshness-missing-generated-at",
    ])
    def test_broken_bundle_fails_verify(self, fixture_name):
        fixture_dir = _BROKEN_BUNDLES / fixture_name
        if not fixture_dir.exists():
            pytest.skip(f"fixture not found: {fixture_dir}")
        code, errors, _ = audit_root(fixture_dir, strict=True)
        assert code != 0, (
            f"FAIL-OPEN: broken bundle '{fixture_name}' passed verify — "
            f"expected non-zero return. errors={errors}"
        )

    @pytest.mark.parametrize("fixture_name,expected_error_fragment", [
        ("missing-allowed-actions", "allowed-actions.json"),
        ("bad-task-card-type", "target_agents"),
        ("source-map-missing-claims", "claims"),
        ("freshness-missing-generated-at", "generated_at"),
    ])
    def test_broken_bundle_error_message_is_specific(self, fixture_name, expected_error_fragment):
        fixture_dir = _BROKEN_BUNDLES / fixture_name
        if not fixture_dir.exists():
            pytest.skip(f"fixture not found: {fixture_dir}")
        _, errors, warnings = audit_root(fixture_dir, strict=True)
        combined = "\n".join(errors + warnings)
        assert expected_error_fragment in combined, (
            f"expected '{expected_error_fragment}' in errors for '{fixture_name}', "
            f"got: {combined!r}"
        )

    def test_negative_fixtures_command_all_pass(self):
        """The negative-fixtures CLI command must confirm every fixture fails as expected."""
        if not _NEGATIVE_MANIFEST.exists():
            pytest.skip("negative fixture manifest not found")
        args = argparse.Namespace(manifest=str(_NEGATIVE_MANIFEST), json=True)
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = negative_fixtures(args)
        data = json.loads(buf.getvalue())
        assert data["status"] == "ok", (
            f"negative-fixtures command had failures: {data.get('failures', [])}"
        )
        assert data["passed"] == data["count"], (
            f"expected all {data['count']} to pass, got {data['passed']}"
        )
        assert rc == 0


# ---------------------------------------------------------------------------
# AP-012 — programmatically constructed adversarial bundles
# ---------------------------------------------------------------------------

class TestProgrammaticAdversarialBundles:
    """Build broken bundles dynamically and assert fail-closed in each case."""

    def test_empty_directory_fails(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        code, errors, _ = audit_root(empty, strict=True)
        assert code != 0
        assert any("missing required file" in e for e in errors)

    def test_missing_llms_txt_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        (bd / "llms.txt").unlink()
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0
        assert any("llms.txt" in e for e in errors)

    def test_missing_agent_entrypoint_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        (bd / "AGENT_ENTRYPOINT.md").unlink()
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0

    def test_missing_disclaimer_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        (bd / "disclaimer.md").unlink()
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0

    def test_missing_citation_cff_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        (bd / "CITATION.cff").unlink()
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0

    def test_missing_source_map_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        (bd / "source-map.json").unlink()
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0
        assert any("source-map.json" in e for e in errors)

    def test_missing_freshness_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        (bd / "freshness.json").unlink()
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0
        assert any("freshness.json" in e for e in errors)

    def test_missing_allowed_actions_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        (bd / "allowed-actions.json").unlink()
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0
        assert any("allowed-actions.json" in e for e in errors)

    def test_malformed_json_task_card_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        (bd / "agent-task-card.json").write_text("{broken json---", encoding="utf-8")
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0

    def test_task_card_with_string_instead_of_array_target_agents_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        card = json.loads((bd / "agent-task-card.json").read_text())
        card["target_agents"] = "claude"  # wrong type: string instead of array
        (bd / "agent-task-card.json").write_text(json.dumps(card), encoding="utf-8")
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0
        assert any("target_agents" in e for e in errors)

    def test_task_card_missing_required_field_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        card = json.loads((bd / "agent-task-card.json").read_text())
        del card["title"]
        (bd / "agent-task-card.json").write_text(json.dumps(card), encoding="utf-8")
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0

    def test_source_map_missing_claims_field_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        sm = json.loads((bd / "source-map.json").read_text())
        del sm["claims"]
        (bd / "source-map.json").write_text(json.dumps(sm), encoding="utf-8")
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0
        assert any("claims" in e for e in errors)

    def test_freshness_missing_generated_at_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        fr = json.loads((bd / "freshness.json").read_text())
        del fr["generated_at"]
        (bd / "freshness.json").write_text(json.dumps(fr), encoding="utf-8")
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0
        assert any("generated_at" in e for e in errors)

    def test_agent_entrypoint_missing_primary_task_section_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        (bd / "AGENT_ENTRYPOINT.md").write_text(
            "# Entrypoint\nInput contract: none\nExpected output schema: none\nallowed-actions: read\n",
            encoding="utf-8",
        )
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0
        assert any("Primary task" in e for e in errors)

    def test_agent_entrypoint_missing_input_contract_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        (bd / "AGENT_ENTRYPOINT.md").write_text(
            "# Entrypoint\nPrimary task: test\nExpected output schema: none\nallowed-actions: read\n",
            encoding="utf-8",
        )
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0
        assert any("Input contract" in e for e in errors)

    def test_agent_entrypoint_missing_output_schema_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        (bd / "AGENT_ENTRYPOINT.md").write_text(
            "# Entrypoint\nPrimary task: test\nInput contract: none\nallowed-actions: read\n",
            encoding="utf-8",
        )
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0
        assert any("Expected output schema" in e for e in errors)

    def test_no_allowed_actions_disclaimer_in_bundle_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        # Strip all mentions of allowed-actions from prose files
        for fname in ("AGENT_ENTRYPOINT.md", "disclaimer.md", "citation-policy.md"):
            p = bd / fname
            p.write_text(p.read_text().replace("allowed-actions", ""), encoding="utf-8")
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0
        assert any("allowed-actions" in e for e in errors)

    def test_invalid_sitemap_xml_fails(self, tmp_path):
        bd = _make_valid_bundle(tmp_path)
        (bd / "sitemap.xml").write_text("<not>valid<xml>", encoding="utf-8")
        code, errors, _ = audit_root(bd, strict=True)
        assert code != 0


# ---------------------------------------------------------------------------
# AP-012 — verify CLI wrapper also fails closed
# ---------------------------------------------------------------------------

class TestVerifyCLIFailsClosed:
    """Ensure the `verify` CLI function (not just audit_root) returns non-zero."""

    def test_verify_returns_nonzero_for_empty_bundle(self, tmp_path, capsys):
        empty = tmp_path / "empty"
        empty.mkdir()
        args = _verify_args(empty)
        rc = verify(args)
        capsys.readouterr()
        assert rc != 0

    def test_verify_json_output_status_fail_for_broken_bundle(self, tmp_path, capsys):
        bd = _make_valid_bundle(tmp_path)
        (bd / "allowed-actions.json").unlink()
        args = _verify_args(bd)
        rc = verify(args)
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "fail"
        assert rc != 0

    def test_verify_json_errors_list_non_empty_for_broken_bundle(self, tmp_path, capsys):
        bd = _make_valid_bundle(tmp_path)
        (bd / "freshness.json").unlink()
        args = _verify_args(bd)
        verify(args)
        data = json.loads(capsys.readouterr().out)
        assert len(data["errors"]) > 0

    def test_verify_returns_zero_for_valid_bundle(self, tmp_path, capsys):
        bd = _make_valid_bundle(tmp_path)
        args = _verify_args(bd)
        rc = verify(args)
        data = json.loads(capsys.readouterr().out)
        assert rc == 0, f"valid bundle failed verify: {data['errors']}"
        assert data["status"] == "ok"
