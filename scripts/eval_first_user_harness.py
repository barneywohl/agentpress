#!/usr/bin/env python3
"""Safe first-user AgentPress CLI eval harness.

Creates synthetic repositories under /tmp, runs local first-contact AgentPress
commands, records whether a fresh agent/user gets actionable help, and cleans up
all generated repos by default.

No network outreach, package publishing, or writes outside the configured status
file are performed by this harness.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_STATUS_OUT = pathlib.Path(
    "/Volumes/X10/clawd/shared/status/agentpress_karpathy_mini_eval_harness_20260505.md"
)
DEFAULT_SCENARIOS = (
    "empty-repo",
    "js-app",
    "python-package",
    "messy-docs",
    "missing-readme",
    "monorepo-ish",
    "docs-only",
)


@dataclass(frozen=True)
class CommandSpec:
    name: str
    argv: tuple[str, ...]
    expect_success: bool = True
    checks_actionability: bool = False


def _write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


def create_scenario(root: pathlib.Path, name: str) -> pathlib.Path:
    """Create a small synthetic repo scenario under root and return its path."""
    repo = root / name
    repo.mkdir(parents=True, exist_ok=False)
    if name == "empty-repo":
        return repo
    if name == "js-app":
        _write(repo / "package.json", '{"name":"demo-js-app","scripts":{"test":"node index.js"}}\n')
        _write(repo / "index.js", "console.log('hello agentpress');\n")
        _write(repo / "README.md", "# Demo JS app\n\nTiny JavaScript app needing agent onboarding.\n")
    elif name == "python-package":
        _write(repo / "pyproject.toml", """
        [project]
        name = "demo-python-package"
        version = "0.0.1"
        """)
        _write(repo / "src/demo_pkg/__init__.py", "__all__ = []\n")
        _write(repo / "README.md", "# Demo Python package\n\nSmall Python package.\n")
    elif name == "messy-docs":
        _write(repo / "README.md", """
        demo notes
        ===========

        TODO maybe install somehow. API? Ask Sam. Old command: ./run-old.sh.
        No agent entrypoint yet, multiple stale claims, no citation policy.
        """)
        _write(repo / "docs/notes.md", "Random launch notes with no owner or freshness date.\n")
        _write(repo / "docs/archive/old.md", "Deprecated instructions.\n")
    elif name == "missing-readme":
        _write(repo / "AGENTS.md", "# Agent notes\n\nRun tests before changing code.\n")
        _write(repo / "src/main.py", "print('no readme')\n")
    elif name == "monorepo-ish":
        _write(repo / "README.md", "# Demo monorepo\n\nContains web, api, and docs packages.\n")
        _write(repo / "packages/web/package.json", '{"name":"web"}\n')
        _write(repo / "packages/api/pyproject.toml", "[project]\nname='api'\nversion='0.0.1'\n")
        _write(repo / "docs/README.md", "# Docs\n")
    elif name == "docs-only":
        _write(repo / "README.md", "# Docs only\n\nA documentation-only project with no machine-readable agent surface.\n")
        _write(repo / "llms.txt", "# Docs only\n\nThis is a tiny llms.txt surface.\n")
    else:
        raise ValueError(f"unknown scenario: {name}")
    return repo


def command_specs(cli: tuple[str, ...], scenario: pathlib.Path, scratch: pathlib.Path) -> list[CommandSpec]:
    wizard_out = scratch / "wizard" / scenario.name
    return [
        CommandSpec("help", (*cli, "--help"), expect_success=True),
        CommandSpec("doctor-local", (*cli, "doctor", str(scenario), "--mode", "local", "--json"), expect_success=False, checks_actionability=True),
        CommandSpec("lint-no-write", (*cli, "lint", str(scenario), "--no-write", "--json", "--allow-warnings"), expect_success=True, checks_actionability=True),
        CommandSpec("first-run-wizard", (*cli, "first-run-wizard", str(scenario), "--out", str(wizard_out), "--no-write", "--json"), expect_success=True, checks_actionability=True),
        CommandSpec("first-user-bootstrap", (*cli, "first-user-bootstrap", "--platform", "generic", "--out", str(scratch / "bootstrap" / scenario.name), "--no-write", "--json"), expect_success=True, checks_actionability=True),
    ]


def run_command(spec: CommandSpec, cwd: pathlib.Path, timeout: int) -> dict:
    started = time.time()
    try:
        proc = subprocess.run(
            spec.argv,
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env={**os.environ, "NO_COLOR": "1"},
        )
        duration_ms = int((time.time() - started) * 1000)
        output = (proc.stdout + "\n" + proc.stderr).strip()
        parsed = None
        if output.startswith("{") or output.startswith("["):
            try:
                parsed = json.loads(output)
            except json.JSONDecodeError:
                parsed = None
        return {
            "name": spec.name,
            "argv": list(spec.argv),
            "returncode": proc.returncode,
            "duration_ms": duration_ms,
            "expected_success": spec.expect_success,
            "ok": proc.returncode == 0 if spec.expect_success else True,
            "stdout_excerpt": proc.stdout[:3000],
            "stderr_excerpt": proc.stderr[:2000],
            "json": parsed,
            "actionable": assess_actionability(output, parsed) if spec.checks_actionability else proc.returncode == 0,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "name": spec.name,
            "argv": list(spec.argv),
            "returncode": None,
            "duration_ms": int((time.time() - started) * 1000),
            "expected_success": spec.expect_success,
            "ok": False,
            "stdout_excerpt": (exc.stdout or "")[:3000] if isinstance(exc.stdout, str) else "",
            "stderr_excerpt": (exc.stderr or "")[:2000] if isinstance(exc.stderr, str) else "",
            "json": None,
            "actionable": False,
            "timeout": True,
        }


def assess_actionability(output: str, parsed: object | None) -> bool:
    text = output.lower()
    tokens = ("missing", "entrypoint", "readme", "agent", "next", "fix", "recommend", "command", "status")
    if sum(1 for token in tokens if token in text) >= 2:
        return True
    if isinstance(parsed, dict):
        if parsed.get("errors") or parsed.get("recommendations") or parsed.get("next_steps"):
            return True
        if any(key in parsed for key in ("entrypoints", "checks", "fixes", "status")):
            return True
    return False


def scenario_score(commands: list[dict]) -> dict:
    help_ok = next((c["ok"] for c in commands if c["name"] == "help"), False)
    actionable = [c for c in commands if c.get("actionable")]
    unexpected_failures = [c for c in commands if not c.get("ok")]
    return {
        "help_available": bool(help_ok),
        "actionable_commands": len(actionable),
        "unexpected_failures": [c["name"] for c in unexpected_failures],
        "fresh_user_helpful": bool(help_ok and len(actionable) >= 2 and not unexpected_failures),
    }


def backlog_from_results(results: list[dict]) -> list[dict]:
    backlog: list[dict] = []
    for result in results:
        score = result["score"]
        if not score["fresh_user_helpful"]:
            backlog.append({
                "priority": "P0" if score["unexpected_failures"] else "P1",
                "scenario": result["scenario"],
                "issue": "First-contact flow did not meet helpfulness threshold",
                "evidence": score,
                "recommended_fix": "Make doctor/lint/wizard return concise next-step remediation for sparse or non-AgentPress repos without requiring prior AgentPress knowledge.",
            })
        for command in result["commands"]:
            if command.get("timeout"):
                backlog.append({
                    "priority": "P0",
                    "scenario": result["scenario"],
                    "issue": f"{command['name']} timed out",
                    "recommended_fix": "Add bounded filesystem scanning and clearer progress/timeout handling.",
                })
            elif not command.get("ok"):
                backlog.append({
                    "priority": "P1",
                    "scenario": result["scenario"],
                    "issue": f"{command['name']} had unexpected non-zero exit {command.get('returncode')}",
                    "recommended_fix": "Return zero for advisory first-contact commands or document non-zero semantics in help output.",
                })
            elif command["name"] == "help" and len(command.get("stdout_excerpt", "")) >= 2500:
                backlog.append({
                    "priority": "P2",
                    "scenario": result["scenario"],
                    "issue": "top-level help is too broad for a fresh first user",
                    "recommended_fix": "Add a concise `agentpress start` or first-run section before the full command list with the 3 commands a new agent should try first.",
                })
            elif command["name"] == "doctor-local" and isinstance(command.get("json"), dict) and not any(k in command["json"] for k in ("next_steps", "recommendations", "fixes")):
                backlog.append({
                    "priority": "P2",
                    "scenario": result["scenario"],
                    "issue": "doctor identifies missing entrypoints but does not emit explicit next_steps/recommendations",
                    "recommended_fix": "Add machine-readable next_steps with exact commands such as init/bundle/first-run-wizard and expected output paths.",
                })
            elif command.get("expected_success") and not command.get("actionable") and command["name"] != "help":
                backlog.append({
                    "priority": "P2",
                    "scenario": result["scenario"],
                    "issue": f"{command['name']} output was not clearly actionable",
                    "recommended_fix": "Include next commands, missing files, and a minimal path to green in machine-readable fields.",
                })
    return backlog


def render_markdown(summary: dict) -> str:
    lines = [
        "# AgentPress Karpathy Mini First-User Eval Harness",
        "",
        f"Generated: `{summary['generated_at']}`",
        f"CLI mode: `{summary['cli_mode']}`",
        f"Temp root: `{summary['temp_root']}` (cleaned: `{summary['cleaned']}`)",
        "",
        "## Result",
        "",
        f"- Scenarios: **{summary['scenario_count']}**",
        f"- Fresh-user helpful: **{summary['helpful_count']} / {summary['scenario_count']}**",
        f"- Backlog items: **{len(summary['backlog'])}**",
        "",
        "## Scenario Matrix",
        "",
        "| Scenario | Helpful? | Actionable commands | Unexpected failures |",
        "|---|---:|---:|---|",
    ]
    for result in summary["results"]:
        score = result["score"]
        failures = ", ".join(score["unexpected_failures"]) or "-"
        lines.append(f"| {result['scenario']} | {score['fresh_user_helpful']} | {score['actionable_commands']} | {failures} |")
    lines.extend(["", "## Actionable Build Backlog", ""])
    if summary["backlog"]:
        for i, item in enumerate(summary["backlog"], 1):
            lines.append(f"{i}. **{item['priority']} / {item['scenario']}** — {item['issue']}")
            lines.append(f"   - Fix: {item['recommended_fix']}")
    else:
        lines.append("No backlog items generated by this run.")
    lines.extend(["", "## Command Evidence", ""])
    for result in summary["results"]:
        lines.append(f"### {result['scenario']}")
        for command in result["commands"]:
            lines.append(
                f"- `{command['name']}` rc={command.get('returncode')} ok={command.get('ok')} "
                f"actionable={command.get('actionable')} duration_ms={command.get('duration_ms')}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status-out", default=str(DEFAULT_STATUS_OUT), help="Markdown report path")
    parser.add_argument("--workdir", default=None, help="Temp harness root; defaults to /tmp/agentpress-first-user-eval-*.")
    parser.add_argument("--keep-workdir", action="store_true", help="Keep generated repos for debugging.")
    parser.add_argument("--timeout", type=int, default=20, help="Per-command timeout seconds.")
    parser.add_argument("--scenario", dest="scenarios", action="append", choices=DEFAULT_SCENARIOS, help="Scenario to run; repeatable. Defaults to all.")
    parser.add_argument("--cli", action="append", help="CLI argv token; repeat for custom CLI. Defaults to local python script.")
    parser.add_argument("--cli-mode", default="local-python", help="Label for the CLI under test.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary to stdout.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any scenario is not helpful.")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    cli = tuple(args.cli) if args.cli else (sys.executable, str(REPO_ROOT / "scripts" / "agentpress.py"))
    scenarios = tuple(args.scenarios or DEFAULT_SCENARIOS)
    temp_root = pathlib.Path(args.workdir) if args.workdir else pathlib.Path(tempfile.mkdtemp(prefix="agentpress-first-user-eval-", dir="/tmp"))
    created_temp = not args.workdir
    scratch = temp_root / "_command-scratch"
    results: list[dict] = []
    cleaned = False
    summary: dict | None = None
    exit_code = 0
    status_out = pathlib.Path(args.status_out)
    try:
        temp_root.mkdir(parents=True, exist_ok=True)
        scratch.mkdir(parents=True, exist_ok=True)
        for scenario in scenarios:
            scenario_path = create_scenario(temp_root / "repos", scenario)
            commands = [run_command(spec, scenario_path, args.timeout) for spec in command_specs(cli, scenario_path, scratch)]
            results.append({"scenario": scenario, "path": str(scenario_path), "commands": commands, "score": scenario_score(commands)})
        backlog = backlog_from_results(results)
        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cli_mode": args.cli_mode,
            "cli": list(cli),
            "temp_root": str(temp_root),
            "cleaned": False,
            "scenario_count": len(results),
            "helpful_count": sum(1 for result in results if result["score"]["fresh_user_helpful"]),
            "results": results,
            "backlog": backlog,
        }
        exit_code = 1 if args.strict and summary["helpful_count"] != summary["scenario_count"] else 0
    finally:
        if not args.keep_workdir:
            # Guardrail: only remove generated harness dirs under /tmp.
            resolved = temp_root.resolve()
            resolved_s = str(resolved)
            if (
                resolved_s.startswith("/tmp/agentpress-first-user-eval-")
                or resolved_s.startswith("/private/tmp/agentpress-first-user-eval-")
                or (created_temp and (resolved_s.startswith("/tmp/") or resolved_s.startswith("/private/tmp/")))
            ):
                shutil.rmtree(resolved, ignore_errors=True)
                cleaned = True
        if summary is not None:
            summary["cleaned"] = cleaned
            status_out.parent.mkdir(parents=True, exist_ok=True)
            status_out.write_text(render_markdown(summary), encoding="utf-8")
            if args.json:
                print(json.dumps(summary, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
