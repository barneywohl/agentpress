"""`agentpress doctor` — repo health check. Mirrors bin/lib/doctor.js."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from agentpress_core import SPEC_VERSION, parse, validate

from . import _exit_codes as EXIT
from ._paths import resolve_agents_txt, root_or_cwd, to_posix
from ._version import __version__


HELP = """Usage: agentpress doctor [path] [options]

Run a comprehensive health check on the v1.0 surface for a repo.

Options:
  --json        Emit JSON output instead of the human-readable checklist.
  -h, --help    Show this help.

Exit codes:
  0  all checks pass (warnings allowed)
  1  one or more errors
"""


def _check_python_version() -> dict:
    ok = sys.version_info >= (3, 10)
    return {
        "name": "Python >= 3.10",
        "status": "pass" if ok else "fail",
        "detail": f"python {sys.version.split()[0]}",
    }


def _check_node_available() -> dict:
    n = shutil.which("node")
    if not n:
        return {"name": "node available (optional, for legacy commands)", "status": "warn", "detail": "not found"}
    try:
        out = subprocess.run(
            [n, "--version"], capture_output=True, text=True, timeout=5
        ).stdout.strip()
        return {
            "name": "node available (optional, for legacy commands)",
            "status": "pass",
            "detail": out,
        }
    except (OSError, subprocess.TimeoutExpired):
        return {
            "name": "node available (optional, for legacy commands)",
            "status": "warn",
            "detail": "could not query --version",
        }


def _check_core_parser_loadable() -> dict:
    try:
        return {
            "name": "agentpress-core parser loadable",
            "status": "pass",
            "detail": f"spec v{SPEC_VERSION}",
        }
    except Exception as exc:  # noqa: BLE001
        return {"name": "agentpress-core parser loadable", "status": "fail", "detail": str(exc)}


def _check_agents_txt_exists(target: Path) -> dict:
    if target.exists():
        return {"name": "agents.txt exists", "status": "pass", "detail": to_posix(target)}
    return {
        "name": "agents.txt exists",
        "status": "fail",
        "detail": f"missing at {to_posix(target)} — run `agentpress init`",
    }


def _check_agents_txt_parses(target: Path) -> dict:
    if not target.exists():
        return {"name": "agents.txt parses", "status": "skip", "detail": "no file"}
    try:
        parse(target.read_text(encoding="utf-8"))
        return {"name": "agents.txt parses", "status": "pass"}
    except Exception as exc:  # noqa: BLE001
        return {"name": "agents.txt parses", "status": "fail", "detail": str(exc)}


def _check_agents_txt_validates(target: Path) -> dict:
    if not target.exists():
        return {"name": "agents.txt validates", "status": "skip", "detail": "no file"}
    try:
        data = parse(target.read_text(encoding="utf-8"))
        r = validate(data)
        errs = sum(1 for i in r.issues if i.severity == "error")
        warns = sum(1 for i in r.issues if i.severity == "warning")
        if errs:
            return {"name": "agents.txt validates", "status": "fail", "detail": f"{errs} error(s)"}
        if warns:
            return {
                "name": "agents.txt validates",
                "status": "warn",
                "detail": f"{warns} warning(s)",
            }
        return {"name": "agents.txt validates", "status": "pass"}
    except Exception as exc:  # noqa: BLE001
        return {"name": "agents.txt validates", "status": "fail", "detail": str(exc)}


def _check_workflow(root: Path) -> dict:
    wf = root / ".github" / "workflows" / "agentstxt.yml"
    workflows_dir = root / ".github" / "workflows"
    if wf.exists():
        return {"name": ".github/workflows/agentstxt.yml present", "status": "pass"}
    if workflows_dir.exists():
        return {
            "name": ".github/workflows/agentstxt.yml present",
            "status": "warn",
            "detail": "GitHub Actions configured but agents.txt workflow missing",
        }
    return {
        "name": ".github/workflows/agentstxt.yml present",
        "status": "skip",
        "detail": "no .github/workflows dir",
    }


def _check_readme_badge(root: Path) -> dict:
    readme = root / "README.md"
    if not readme.exists():
        return {"name": "README badge present", "status": "skip", "detail": "no README.md"}
    content = readme.read_text(encoding="utf-8", errors="ignore")
    import re

    if re.search(r"agents\.txt-v1\.0", content) or re.search(r"img\.shields\.io.*agents\.txt", content):
        return {"name": "README badge present", "status": "pass"}
    return {
        "name": "README badge present",
        "status": "warn",
        "detail": "no agents.txt badge detected",
    }


def _check_on_path() -> dict:
    cmd = shutil.which("agentpress")
    if cmd:
        return {"name": "agentpress on PATH", "status": "pass", "detail": cmd}
    return {
        "name": "agentpress on PATH",
        "status": "warn",
        "detail": "not found (you may be running via pipx)",
    }


def run_doctor(argv: list[str]) -> int:
    json_out = False
    path_arg: str | None = None
    for a in argv:
        if a == "--json":
            json_out = True
        elif a in ("-h", "--help"):
            sys.stdout.write(HELP)
            return EXIT.OK
        elif not a.startswith("-"):
            path_arg = a

    root = Path(path_arg).resolve() if path_arg else root_or_cwd()
    target = resolve_agents_txt(path_arg)

    checks = [
        _check_python_version(),
        _check_node_available(),
        _check_core_parser_loadable(),
        _check_agents_txt_exists(target),
        _check_agents_txt_parses(target),
        _check_agents_txt_validates(target),
        _check_workflow(root),
        _check_readme_badge(root),
        _check_on_path(),
    ]

    counts = {"pass": 0, "warn": 0, "fail": 0, "skip": 0}
    for c in checks:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    ok = counts["fail"] == 0

    if json_out:
        sys.stdout.write(
            json.dumps(
                {
                    "ok": ok,
                    "version": __version__,
                    "root": to_posix(root),
                    "checks": checks,
                    "summary": counts,
                }
            )
            + "\n"
        )
    else:
        sys.stdout.write(f"AgentPress doctor (v{__version__})\n")
        sys.stdout.write(f"  root: {to_posix(root)}\n\n")
        for c in checks:
            icon = {"pass": "✓", "warn": "⚠", "fail": "✗", "skip": "·"}.get(c["status"], "?")
            detail = f"  ({c['detail']})" if c.get("detail") else ""
            sys.stdout.write(f"  {icon} {c['name']}{detail}\n")
        sys.stdout.write(
            f"\nSummary: {counts['pass']} OK, {counts['warn']} warning(s), {counts['fail']} error(s)"
        )
        if counts["skip"]:
            sys.stdout.write(f", {counts['skip']} skipped")
        sys.stdout.write(".\n")
        sys.stdout.write("System healthy.\n" if ok else "See errors above.\n")

    return EXIT.OK if ok else EXIT.ERRORS_FOUND
