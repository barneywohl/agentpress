import argparse
import json

from scripts.agentpress import broker_preenqueue_check, broker_scope_guard


def _args(path, **overrides):
    data = {
        "path": str(path),
        "out": str(path.parent / "guard.json"),
        "require_text": ["agentpress"],
        "allowed_token": ["agentpress"],
        "banned_token": ["korea", "value-hunter", "article"],
        "require_allowed_root": False,
        "enforce": False,
        "no_write": False,
        "strict": False,
        "json": True,
    }
    data.update(overrides)
    return argparse.Namespace(**data)


def test_broker_scope_guard_rejects_cross_scope_root(tmp_path, capsys):
    task = tmp_path / "task.json"
    task.write_text(json.dumps({
        "task": "AgentPress build mission",
        "allowed_roots": ["/Volumes/X10/clawd/korea-value-hunter-research"],
    }), encoding="utf-8")

    rc = broker_scope_guard(_args(task))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "fail"
    assert data["fail_count"] == 1
    assert data["findings"][0]["code"] == "cross_scope_root"


def test_broker_scope_guard_allows_agentpress_root(tmp_path, capsys):
    task = tmp_path / "task.json"
    task.write_text(json.dumps({
        "task": "AgentPress build mission",
        "allowed_roots": ["/tmp/agentpress-publish-commit"],
    }), encoding="utf-8")

    rc = broker_scope_guard(_args(task))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "ok"
    assert data["findings"] == []


def test_broker_preenqueue_check_blocks_cross_scope_before_enqueue(tmp_path, capsys):
    task = tmp_path / "task.json"
    task.write_text(json.dumps({
        "task": "AgentPress mission should stay scoped",
        "workdir": "/Volumes/X10/clawd/korea-value-hunter-research",
    }), encoding="utf-8")

    rc = broker_preenqueue_check(_args(task, enforce=True, strict=True, no_write=True))
    data = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert data["status"] == "blocked"
    assert data["enqueue_allowed"] is False
    assert data["integration_contract"]["call_before_enqueue"] is True
    assert data["guard_findings"][0]["code"] == "cross_scope_root"


def test_broker_preenqueue_check_allows_agentpress_task(tmp_path, capsys):
    task = tmp_path / "task.json"
    task.write_text(json.dumps({
        "task": "AgentPress mission can enqueue",
        "workdir": "/tmp/agentpress-main-reconcile",
    }), encoding="utf-8")

    rc = broker_preenqueue_check(_args(task, enforce=True, strict=True, no_write=True))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "pass"
    assert data["enqueue_allowed"] is True
    assert data["guard_status"] == "ok"
