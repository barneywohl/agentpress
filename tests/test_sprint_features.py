"""
Tests for the AgentPress 8-hour sprint features.

Covers: first-user-bootstrap, proof-capture, sandbox-guard,
        adoption-tracker, handoff-pack, batch-painpoints.

Run: pytest tests/test_sprint_features.py -v
"""
import argparse
import importlib.util
import json
import os
import pathlib

import pytest

# ---------------------------------------------------------------------------
# Module import — load agentpress.py once for the entire test session
# ---------------------------------------------------------------------------
_SCRIPTS = pathlib.Path(__file__).parent.parent / "scripts"
_SPEC = importlib.util.spec_from_file_location("agentpress", _SCRIPTS / "agentpress.py")
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

first_user_bootstrap = _MOD.first_user_bootstrap
proof_capture = _MOD.proof_capture
sandbox_guard = _MOD.sandbox_guard
adoption_tracker = _MOD.adoption_tracker
handoff_pack = _MOD.handoff_pack
batch_painpoints = _MOD.batch_painpoints
doctor = _MOD.doctor
external_proof_run = _MOD.external_proof_run


def _ns(**kwargs) -> argparse.Namespace:
    """Return a Namespace with safe defaults for all sprint commands."""
    base = {
        "base_url": "https://example.com/agentpress/",
        "no_write": True,
        "json": True,
        "strict": False,
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


# ===========================================================================
# first-user-bootstrap
# ===========================================================================

class TestFirstUserBootstrap:
    def test_cline_returns_ready_for_paste(self, tmp_path, capsys):
        args = _ns(platform="cline", out=str(tmp_path / "bs.json"))
        rc = first_user_bootstrap(args)
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "ready_for_paste"
        assert data["platform"] == "cline"
        assert rc == 0

    @pytest.mark.parametrize("platform", ["cline", "roo", "claude", "cursor", "windsurf", "generic"])
    def test_all_supported_platforms_ready(self, tmp_path, capsys, platform):
        args = _ns(platform=platform, out=str(tmp_path / f"bs-{platform}.json"))
        rc = first_user_bootstrap(args)
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "ready_for_paste", f"{platform}: expected ready_for_paste"
        assert rc == 0

    def test_unsupported_platform_flagged(self, tmp_path, capsys):
        args = _ns(platform="vim", out=str(tmp_path / "bs.json"))
        first_user_bootstrap(args)
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "unsupported_platform"
        assert data["finding_count"] >= 1

    def test_strict_flag_nonzero_on_unsupported(self, tmp_path, capsys):
        args = _ns(platform="unknown_host", out=str(tmp_path / "bs.json"), strict=True)
        rc = first_user_bootstrap(args)
        capsys.readouterr()
        assert rc != 0

    def test_steps_present_and_ordered(self, tmp_path, capsys):
        args = _ns(platform="cline", out=str(tmp_path / "bs.json"))
        first_user_bootstrap(args)
        data = json.loads(capsys.readouterr().out)
        steps = data["steps"]
        assert len(steps) >= 4
        nums = [s["step"] for s in steps]
        assert nums == sorted(nums), "steps not in order"

    def test_mcp_snippet_requires_approval(self, tmp_path, capsys):
        args = _ns(platform="cline", out=str(tmp_path / "bs.json"))
        first_user_bootstrap(args)
        data = json.loads(capsys.readouterr().out)
        snippet = json.dumps(data.get("mcp_snippet", {}))
        assert "approval_required" in snippet

    def test_no_external_posts_in_safety(self, tmp_path, capsys):
        args = _ns(platform="cline", out=str(tmp_path / "bs.json"))
        first_user_bootstrap(args)
        data = json.loads(capsys.readouterr().out)
        assert data.get("safety", {}).get("external_posts") is False

    def test_output_contains_no_secrets(self, tmp_path, capsys):
        args = _ns(platform="claude", out=str(tmp_path / "bs.json"))
        first_user_bootstrap(args)
        raw = capsys.readouterr().out
        assert "sk-" not in raw
        assert "PRIVATE KEY" not in raw
        assert "clawd_secrets" not in raw

    def test_no_write_produces_no_file(self, tmp_path, capsys):
        out_path = tmp_path / "bs.json"
        args = _ns(platform="cline", out=str(out_path), no_write=True)
        first_user_bootstrap(args)
        capsys.readouterr()
        assert not out_path.exists(), "no_write=True should not create file"

    def test_write_creates_file(self, tmp_path, capsys):
        out_path = tmp_path / "bs.json"
        args = _ns(platform="cline", out=str(out_path), no_write=False)
        first_user_bootstrap(args)
        capsys.readouterr()
        assert out_path.exists(), "no_write=False should create file"
        data = json.loads(out_path.read_text())
        assert data["status"] == "ready_for_paste"


# ===========================================================================
# proof-capture
# ===========================================================================

class TestProofCapture:
    def _args(self, tmp_path, **kw):
        defaults = dict(
            task_id="test-001",
            evidence_dir=str(tmp_path),
            artifacts="",
            commands="",
            summary="",
            review_required=False,
            no_write=False,
            json=True,
            strict=False,
        )
        defaults.update(kw)
        return argparse.Namespace(**defaults)

    def test_creates_bundle_json(self, tmp_path, capsys):
        proof_capture(self._args(tmp_path))
        capsys.readouterr()
        assert (tmp_path / "proof-bundle.json").exists()

    def test_creates_proof_card_md(self, tmp_path, capsys):
        proof_capture(self._args(tmp_path))
        capsys.readouterr()
        assert (tmp_path / "proof-card.md").exists()

    def test_bundle_sha256_is_64_chars(self, tmp_path, capsys):
        proof_capture(self._args(tmp_path, task_id="sha-test"))
        data = json.loads(capsys.readouterr().out)
        assert "bundle_sha256" in data
        assert len(data["bundle_sha256"]) == 64

    def test_task_id_preserved_in_output(self, tmp_path, capsys):
        proof_capture(self._args(tmp_path, task_id="mission-20260504-053454-927a17"))
        data = json.loads(capsys.readouterr().out)
        assert data["task_id"] == "mission-20260504-053454-927a17"

    def test_existing_artifact_hashed_and_counted(self, tmp_path, capsys):
        artifact = tmp_path / "result.txt"
        artifact.write_text("agentpress sprint output")
        proof_capture(self._args(tmp_path, artifacts=str(artifact)))
        data = json.loads(capsys.readouterr().out)
        assert data["artifact_count"] == 1

    def test_secret_scan_detects_openai_key_pattern(self, tmp_path, capsys):
        secret_file = tmp_path / "leaked.txt"
        secret_file.write_text("sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890")
        proof_capture(self._args(tmp_path, artifacts=str(secret_file)))
        data = json.loads(capsys.readouterr().out)
        assert data["secret_scan_status"] == "secret_hits_found"

    def test_clean_file_passes_secret_scan(self, tmp_path, capsys):
        clean = tmp_path / "clean.txt"
        clean.write_text("All clear — no secrets here.")
        proof_capture(self._args(tmp_path, artifacts=str(clean)))
        data = json.loads(capsys.readouterr().out)
        assert data["secret_scan_status"] == "no_obvious_secrets"

    def test_missing_artifact_recorded_as_missing(self, tmp_path, capsys):
        proof_capture(self._args(tmp_path, artifacts="/tmp/does-not-exist-999.txt"))
        bundle = json.loads((tmp_path / "proof-bundle.json").read_text())
        capsys.readouterr()
        assert any(a.get("missing") for a in bundle["artifacts"])

    def test_bundle_json_is_valid_json(self, tmp_path, capsys):
        proof_capture(self._args(tmp_path))
        capsys.readouterr()
        bundle_path = tmp_path / "proof-bundle.json"
        data = json.loads(bundle_path.read_text())  # raises on bad JSON
        assert data["status"] == "ok"

    def test_proof_card_contains_task_id(self, tmp_path, capsys):
        proof_capture(self._args(tmp_path, task_id="card-task"))
        capsys.readouterr()
        card = (tmp_path / "proof-card.md").read_text()
        assert "card-task" in card


# ===========================================================================
# sandbox-guard
# ===========================================================================

class TestSandboxGuard:
    def _args(self, tmp_path, **kw):
        defaults = dict(
            scope="read-only",
            paths="./src",
            out=str(tmp_path / "sandbox.json"),
            base_url="https://example.com/",
            no_write=True,
            json=True,
            strict=False,
        )
        defaults.update(kw)
        return argparse.Namespace(**defaults)

    def test_clean_read_only_returns_ok(self, tmp_path, capsys):
        rc = sandbox_guard(self._args(tmp_path))
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "ok"
        assert rc == 0

    def test_ssh_path_is_flagged(self, tmp_path, capsys):
        sandbox_guard(self._args(tmp_path, paths="/home/user/.ssh/id_rsa"))
        data = json.loads(capsys.readouterr().out)
        assert data["finding_count"] >= 1
        assert data["status"] in ("fail_closed", "fail")

    def test_wallet_path_is_flagged(self, tmp_path, capsys):
        sandbox_guard(self._args(tmp_path, paths="/Users/user/wallet/keys"))
        data = json.loads(capsys.readouterr().out)
        assert data["finding_count"] >= 1

    def test_clawd_secrets_path_is_flagged(self, tmp_path, capsys):
        sandbox_guard(self._args(tmp_path, paths="/home/user/clawd_secrets/tokens.json"))
        data = json.loads(capsys.readouterr().out)
        assert data["finding_count"] >= 1

    def test_invalid_scope_flagged(self, tmp_path, capsys):
        sandbox_guard(self._args(tmp_path, scope="superuser"))
        data = json.loads(capsys.readouterr().out)
        assert data["finding_count"] >= 1

    def test_scope_field_in_output(self, tmp_path, capsys):
        sandbox_guard(self._args(tmp_path, scope="read-only"))
        data = json.loads(capsys.readouterr().out)
        assert data["scope"] == "read-only"

    def test_policy_default_deny_secrets_true(self, tmp_path, capsys):
        sandbox_guard(self._args(tmp_path))
        data = json.loads(capsys.readouterr().out)
        assert data["policy"]["default_deny_secrets"] is True

    def test_policy_external_effects_require_approval(self, tmp_path, capsys):
        sandbox_guard(self._args(tmp_path))
        data = json.loads(capsys.readouterr().out)
        assert data["policy"]["external_effects_require_approval"] is True

    def test_no_write_false_creates_wrapper_script(self, tmp_path, capsys):
        out_path = tmp_path / "sandbox.json"
        args = self._args(tmp_path, out=str(out_path), no_write=False)
        sandbox_guard(args)
        capsys.readouterr()
        wrapper = out_path.with_suffix(".sh")
        assert wrapper.exists(), "wrapper .sh not created"
        assert os.access(wrapper, os.X_OK), "wrapper script not executable"

    def test_wrapper_blocks_sensitive_paths(self, tmp_path, capsys):
        out_path = tmp_path / "sandbox.json"
        args = self._args(tmp_path, out=str(out_path), no_write=False)
        sandbox_guard(args)
        capsys.readouterr()
        wrapper_text = out_path.with_suffix(".sh").read_text()
        assert "clawd_secrets" in wrapper_text
        assert ".ssh" in wrapper_text
        assert "exit 64" in wrapper_text


# ===========================================================================
# adoption-tracker
# ===========================================================================

class TestAdoptionTracker:
    def _args(self, tmp_path, **kw):
        defaults = dict(
            period="7d",
            root=str(tmp_path),
            out=str(tmp_path / "adoption.json"),
            base_url="https://example.com/",
            no_write=True,
            json=True,
        )
        defaults.update(kw)
        return argparse.Namespace(**defaults)

    def test_empty_root_returns_ok(self, tmp_path, capsys):
        rc = adoption_tracker(self._args(tmp_path, root=str(tmp_path / "empty")))
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "ok"
        assert rc == 0

    def test_all_funnel_stages_present(self, tmp_path, capsys):
        adoption_tracker(self._args(tmp_path))
        data = json.loads(capsys.readouterr().out)
        expected = ["install_attempted", "doctor_ok", "proof_created",
                    "outreach_ready", "external_reply", "issue_or_pr"]
        for stage in expected:
            assert stage in data["funnel"], f"missing funnel stage: {stage}"

    def test_install_receipt_increments_install_stage(self, tmp_path, capsys):
        receipt = tmp_path / "install_receipt.json"
        receipt.write_text(json.dumps({"action": "install", "status": "ok"}))
        adoption_tracker(self._args(tmp_path))
        data = json.loads(capsys.readouterr().out)
        assert data["funnel"]["install_attempted"] >= 1

    def test_doctor_ok_receipt_increments_doctor_stage(self, tmp_path, capsys):
        receipt = tmp_path / "dr.json"
        receipt.write_text(json.dumps({"doctor": "ok", "status": "ok"}))
        adoption_tracker(self._args(tmp_path))
        data = json.loads(capsys.readouterr().out)
        assert data["funnel"]["doctor_ok"] >= 1

    def test_proof_receipt_increments_proof_stage(self, tmp_path, capsys):
        receipt = tmp_path / "proof.json"
        receipt.write_text(json.dumps({"schema": "agentpress-proof-capture", "proof-bundle": "path"}))
        adoption_tracker(self._args(tmp_path))
        data = json.loads(capsys.readouterr().out)
        assert data["funnel"]["proof_created"] >= 1

    def test_conversion_rates_bounded_0_to_1(self, tmp_path, capsys):
        adoption_tracker(self._args(tmp_path))
        data = json.loads(capsys.readouterr().out)
        for conv in data.get("conversion", []):
            assert 0.0 <= conv["rate"] <= 1.0, f"rate {conv['rate']} out of range"

    def test_privacy_note_no_ip_tracking(self, tmp_path, capsys):
        adoption_tracker(self._args(tmp_path))
        data = json.loads(capsys.readouterr().out)
        assert "privacy" in data
        assert "no" in data["privacy"].lower()

    def test_period_field_preserved(self, tmp_path, capsys):
        adoption_tracker(self._args(tmp_path, period="30d"))
        data = json.loads(capsys.readouterr().out)
        assert data["period"] == "30d"


# ===========================================================================
# handoff-pack
# ===========================================================================

class TestHandoffPack:
    def _args(self, tmp_path, **kw):
        defaults = dict(
            from_agent="glm",
            to_agent="rflo_sonnet_2",
            task_id="mission-20260504-053454-927a17",
            objective="Implement sprint features",
            constraints="no external posts",
            evidence="",
            acceptance="",
            pending_actions="",
            out=str(tmp_path / "handoff.json"),
            base_url="https://example.com/",
            no_write=True,
            json=True,
        )
        defaults.update(kw)
        return argparse.Namespace(**defaults)

    def test_status_is_ready(self, tmp_path, capsys):
        handoff_pack(self._args(tmp_path))
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "ready"

    def test_from_to_task_id_preserved(self, tmp_path, capsys):
        handoff_pack(self._args(tmp_path))
        data = json.loads(capsys.readouterr().out)
        assert data["from_agent"] == "glm"
        assert data["to_agent"] == "rflo_sonnet_2"
        assert data["task_id"] == "mission-20260504-053454-927a17"

    def test_acceptance_gates_present(self, tmp_path, capsys):
        handoff_pack(self._args(tmp_path))
        data = json.loads(capsys.readouterr().out)
        assert "acceptance_gates" in data
        assert len(data["acceptance_gates"]) >= 1

    def test_handoff_manifest_has_required_keys(self, tmp_path, capsys):
        handoff_pack(self._args(tmp_path))
        data = json.loads(capsys.readouterr().out)
        manifest = data["handoff_manifest"]
        assert "review" in manifest
        assert "do_not" in manifest

    def test_write_creates_json_and_md(self, tmp_path, capsys):
        out_path = tmp_path / "handoff.json"
        args = self._args(tmp_path, out=str(out_path), no_write=False)
        handoff_pack(args)
        capsys.readouterr()
        assert out_path.exists(), "handoff JSON not created"
        assert out_path.with_suffix(".md").exists(), "handoff MD not created"

    def test_md_contains_task_id(self, tmp_path, capsys):
        out_path = tmp_path / "handoff.json"
        args = self._args(tmp_path, out=str(out_path), no_write=False)
        handoff_pack(args)
        capsys.readouterr()
        md_text = out_path.with_suffix(".md").read_text()
        assert "mission-20260504-053454-927a17" in md_text

    def test_custom_acceptance_gates(self, tmp_path, capsys):
        args = self._args(tmp_path, acceptance="gate1,gate2,gate3")
        handoff_pack(args)
        data = json.loads(capsys.readouterr().out)
        gates = data["acceptance_gates"]
        assert "gate1" in gates
        assert "gate2" in gates
        assert "gate3" in gates

    def test_evidence_paths_preserved(self, tmp_path, capsys):
        args = self._args(tmp_path, evidence="/tmp/proof-bundle.json,/tmp/artifact.md")
        handoff_pack(args)
        data = json.loads(capsys.readouterr().out)
        assert "/tmp/proof-bundle.json" in data["evidence_paths"]


# ===========================================================================
# batch-painpoints
# ===========================================================================

class TestBatchPainpoints:
    def _args(self, inp_path, out_path, limit="25", **kw):
        defaults = dict(
            input=str(inp_path),
            output=str(out_path),
            limit=limit,
            base_url="https://example.com/",
            json=True,
        )
        defaults.update(kw)
        return argparse.Namespace(**defaults)

    def test_processes_two_rows(self, tmp_path, capsys):
        inp = tmp_path / "issues.json"
        out = tmp_path / "output"
        rows = [
            {"painpoint": "MCP auth fails on Cline", "host": "cline", "provider": "claude_code", "tool": "bash"},
            {"painpoint": "LangChain checkpoint drift", "host": "langchain", "provider": "openai", "tool": "llm"},
        ]
        inp.write_text(json.dumps(rows))
        rc = batch_painpoints(self._args(inp, out))
        data = json.loads(capsys.readouterr().out)
        assert data["processed_count"] == 2
        assert rc == 0

    def test_approval_required_for_all(self, tmp_path, capsys):
        inp = tmp_path / "issues.json"
        out = tmp_path / "output"
        inp.write_text(json.dumps([{"painpoint": "test", "host": "h", "provider": "p", "tool": "t"}]))
        batch_painpoints(self._args(inp, out))
        data = json.loads(capsys.readouterr().out)
        assert data["approval_required_for_all"] is True

    def test_empty_input_processed_count_zero(self, tmp_path, capsys):
        inp = tmp_path / "empty.json"
        out = tmp_path / "output"
        inp.write_text("[]")
        batch_painpoints(self._args(inp, out))
        data = json.loads(capsys.readouterr().out)
        assert data["processed_count"] == 0

    def test_limit_caps_output(self, tmp_path, capsys):
        inp = tmp_path / "big.json"
        out = tmp_path / "output"
        rows = [{"painpoint": f"issue-{i}", "host": "h", "provider": "p", "tool": "t"} for i in range(30)]
        inp.write_text(json.dumps(rows))
        batch_painpoints(self._args(inp, out, limit="5"))
        data = json.loads(capsys.readouterr().out)
        assert data["processed_count"] <= 5

    def test_creates_summary_json(self, tmp_path, capsys):
        inp = tmp_path / "issues.json"
        out = tmp_path / "output"
        inp.write_text(json.dumps([{"painpoint": "x", "host": "h", "provider": "p", "tool": "t"}]))
        batch_painpoints(self._args(inp, out))
        capsys.readouterr()
        assert (out / "batch-painpoints-summary.json").exists()

    def test_summary_schema_version_present(self, tmp_path, capsys):
        inp = tmp_path / "issues.json"
        out = tmp_path / "output"
        inp.write_text(json.dumps([{"painpoint": "x", "host": "h", "provider": "p", "tool": "t"}]))
        batch_painpoints(self._args(inp, out))
        capsys.readouterr()
        summary = json.loads((out / "batch-painpoints-summary.json").read_text())
        assert "schema_version" in summary

    def test_missing_input_file_processed_zero(self, tmp_path, capsys):
        inp = tmp_path / "nonexistent.json"
        out = tmp_path / "output"
        batch_painpoints(self._args(inp, out))
        data = json.loads(capsys.readouterr().out)
        assert data["processed_count"] == 0

    def test_dict_input_with_issues_key(self, tmp_path, capsys):
        inp = tmp_path / "dict.json"
        out = tmp_path / "output"
        wrapped = {"issues": [
            {"painpoint": "wrapped row", "host": "cline", "provider": "p", "tool": "t"},
        ]}
        inp.write_text(json.dumps(wrapped))
        batch_painpoints(self._args(inp, out))
        data = json.loads(capsys.readouterr().out)
        assert data["processed_count"] == 1

    def test_per_target_json_files_created(self, tmp_path, capsys):
        inp = tmp_path / "issues.json"
        out = tmp_path / "output"
        rows = [{"painpoint": f"p{i}", "host": "h", "provider": "p", "tool": "t"} for i in range(3)]
        inp.write_text(json.dumps(rows))
        batch_painpoints(self._args(inp, out))
        capsys.readouterr()
        json_files = list(out.glob("painpoint-*.json"))
        assert len(json_files) == 3


class TestDoctorOnlineMode:
    def test_auto_from_empty_dir_uses_online_and_passes(self, tmp_path, monkeypatch, capsys):
        def fake_fetch(url, timeout=20):
            return {"url": url, "status": "ok", "http_status": 200, "bytes": 2, "sha256": "0" * 64}
        monkeypatch.setattr(_MOD, "_doctor_fetch_url", fake_fetch)
        rc = doctor(argparse.Namespace(root=str(tmp_path), mode="auto", base_url="https://example.com/agentpress/", timeout=1, json=True))
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["status"] == "ok"
        assert data["mode"] == "online"
        assert len(data["checked_urls"]) == 5

    def test_self_check_does_not_require_local_tree(self, tmp_path, capsys):
        rc = doctor(argparse.Namespace(root=str(tmp_path), mode="self-check", base_url="https://example.com/agentpress/", timeout=1, json=True))
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["mode"] == "self-check"
        assert data["checks"]["json_output_supported"] is True


class TestExternalProofRun:
    def test_external_proof_run_writes_manifest_without_external_write(self, tmp_path, monkeypatch, capsys):
        def ok_json_step(args):
            if hasattr(args, "out") and args.out:
                path = pathlib.Path(args.out)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"status":"ok", "agent_id": getattr(args, "agent_id", "ci-agent")}) + "\n")
            print(json.dumps({"status":"ok"}))
            return 0
        def ok_doctor(args):
            print(json.dumps({"status":"ok", "mode":"online", "checked_urls": []}))
            return 0
        def ok_self_test(args):
            path = pathlib.Path(args.out); path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"status":"pass"}) + "\n")
            print(json.dumps({"status":"ok"}))
            return 0
        def ok_submission(args):
            out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)
            (out / "submission-pack.json").write_text(json.dumps({"status":"ok"}) + "\n")
            print(json.dumps({"status":"ok"}))
            return 0
        def ok_redaction(args):
            pathlib.Path(args.out).write_text(json.dumps({"status":"ok", "checked": 3, "rejected": 0}) + "\n")
            print(json.dumps({"status":"ok", "checked": 3, "rejected": 0}))
            return 0
        monkeypatch.setattr(_MOD, "doctor", ok_doctor)
        monkeypatch.setattr(_MOD, "first_run_wizard", ok_json_step)
        monkeypatch.setattr(_MOD, "self_test", ok_self_test)
        monkeypatch.setattr(_MOD, "landing_receipt", ok_json_step)
        monkeypatch.setattr(_MOD, "submission_pack", ok_submission)
        monkeypatch.setattr(_MOD, "redaction_check", ok_redaction)
        out = tmp_path / "proof"
        rc = external_proof_run(argparse.Namespace(agent_id="ci-agent", runtime="codex", base_url="https://example.com/agentpress/", out=str(out), no_external_write=True, strict=True, json=True))
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["status"] == "ok"
        assert data["human_approval_required_for_external_post"] is True
        assert data["doctor"]["status"] == "pass"
        assert data["receipt"]["status"] == "pass"
        assert data["self_test"]["status"] == "pass"
        assert data["submission"]["status"] == "pass"
        assert data["redaction_check"]["status"] == "ok"
        assert (out / "external-proof-run.json").exists()

    def test_external_proof_run_secret_detection_flags_without_leaking_value(self, tmp_path, monkeypatch, capsys):
        def ok_json_step(args):
            if hasattr(args, "out") and args.out:
                path = pathlib.Path(args.out)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"status":"ok", "agent_id": getattr(args, "agent_id", "ci-agent")}) + "\n")
            print(json.dumps({"status":"ok"}))
            return 0
        def ok_doctor(args):
            print(json.dumps({"status":"ok", "mode":"online", "checked_urls": []}))
            return 0
        def ok_self_test_with_secret(args):
            path = pathlib.Path(args.out); path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"status":"pass", "api_key":"REDACT_ME_TEST_VALUE"}) + "\n")
            print(json.dumps({"status":"ok"}))
            return 0
        def ok_submission(args):
            out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)
            (out / "submission-pack.json").write_text(json.dumps({"status":"ok"}) + "\n")
            print(json.dumps({"status":"ok"}))
            return 0
        monkeypatch.setattr(_MOD, "doctor", ok_doctor)
        monkeypatch.setattr(_MOD, "first_run_wizard", ok_json_step)
        monkeypatch.setattr(_MOD, "self_test", ok_self_test_with_secret)
        monkeypatch.setattr(_MOD, "landing_receipt", ok_json_step)
        monkeypatch.setattr(_MOD, "submission_pack", ok_submission)
        out = tmp_path / "proof"
        rc = external_proof_run(argparse.Namespace(agent_id="ci-agent", runtime="codex", base_url="https://example.com/agentpress/", out=str(out), no_external_write=True, strict=True, json=True))
        stdout = capsys.readouterr().out
        data = json.loads(stdout)
        assert rc != 0
        assert data["status"] == "fail"
        assert data["redaction_check"]["status"] == "fail"
        assert data["redaction_check"]["rejected"] >= 1
        assert "REDACT_ME_TEST_VALUE" not in stdout
