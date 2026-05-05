import argparse
import importlib.util
import json
import pathlib

_SCRIPTS = pathlib.Path(__file__).parent.parent / "scripts"
_SPEC = importlib.util.spec_from_file_location("agentpress", _SCRIPTS / "agentpress.py")
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

tool_output_sample_generate = _MOD.tool_output_sample_generate
smoke_install = _MOD.smoke_install
repo_sync_doctor = _MOD.repo_sync_doctor


def test_tool_output_sample_generate_builds_structured_content(tmp_path, capsys):
    manifest = tmp_path / "tools.json"
    out = tmp_path / "samples.json"
    manifest.write_text(json.dumps({
        "tools": [{
            "name": "weather",
            "description": "Weather",
            "inputSchema": {"type": "object", "properties": {}},
            "outputSchema": {
                "type": "object",
                "properties": {"temperature": {"type": "number"}, "conditions": {"type": "string"}},
                "required": ["temperature", "conditions"],
            },
        }]
    }), encoding="utf-8")

    rc = tool_output_sample_generate(argparse.Namespace(manifest=str(manifest), out=str(out), no_write=False, json=True, strict=True))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "ok"
    assert data["sample_count"] == 1
    assert data["samples"]["weather"]["structuredContent"]["conditions"] == "sample_conditions"
    assert json.loads(out.read_text())["samples"]["weather"]


def test_smoke_install_no_run_plans_both_install_lanes(tmp_path, capsys):
    out = tmp_path / "smoke.json"
    rc = smoke_install(argparse.Namespace(runtime="all", version="", workdir="", out=str(out), timeout_seconds=5, no_run=True, no_write=False, json=True, strict=True))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "ok"
    assert {s["name"] for s in data["steps"]} == {"npm", "pypi"}
    assert all(s["status"] == "planned" for s in data["steps"])


def test_repo_sync_doctor_no_network_reports_dirty_state(tmp_path, capsys):
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "README.md").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "dirty.txt").write_text("dirty", encoding="utf-8")

    rc = repo_sync_doctor(argparse.Namespace(root=str(tmp_path), remote="https://example.com/repo.git", ref="refs/heads/main", out=str(tmp_path / "sync.json"), no_network=True, no_write=True, json=True, strict=False))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "needs_review"
    assert data["dirty_count"] == 1
    assert any(f["code"] == "dirty_worktree" for f in data["findings"])
