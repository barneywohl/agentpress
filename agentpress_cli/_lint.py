"""`agentpress lint` — validate agents.txt. Mirrors bin/lib/lint.js."""
from __future__ import annotations

import json
import sys
from dataclasses import asdict

from agentpress_core import parse, validate

from . import _exit_codes as EXIT
from ._paths import resolve_agents_txt, to_posix


HELP = """Usage: agentpress lint [path] [options]

Validate an agents.txt against the v1.0 spec.

Arguments:
  path                Path to agents.txt or to a directory containing one.
                      Default: ./agents.txt

Options:
  --json              Emit machine-readable JSON output. Default: human.
  --strict            Treat warnings as errors (exit 2 on warnings).
  -h, --help          Show this help.

Exit codes:
  0  valid
  1  errors found
  2  strict-mode warnings escalated, or internal error
  3  agents.txt not found
"""


def _issue_to_dict(issue) -> dict:
    # ValidationIssue is a dataclass — pull fields explicitly to keep schema stable
    return {
        "severity": issue.severity,
        "message": issue.message,
        "section": issue.section,
        "key": issue.key,
    }


def run_lint(argv: list[str]) -> int:
    json_out = False
    strict = False
    path_arg: str | None = None
    for a in argv:
        if a == "--json":
            json_out = True
        elif a == "--strict":
            strict = True
        elif a in ("-h", "--help"):
            sys.stdout.write(HELP)
            return EXIT.OK
        elif not a.startswith("-"):
            path_arg = a

    target = resolve_agents_txt(path_arg)
    if not target.exists():
        msg = f"agents.txt not found at {to_posix(target)}. Run `agentpress init` to create one."
        if json_out:
            sys.stdout.write(
                json.dumps(
                    {"ok": False, "file_not_found": True, "path": to_posix(target), "message": msg}
                )
                + "\n"
            )
        else:
            sys.stderr.write(f"✗ {msg}\n")
        return EXIT.FILE_NOT_FOUND

    text = target.read_text(encoding="utf-8")
    data = parse(text)
    result = validate(data)
    errors = sum(1 for i in result.issues if i.severity == "error")
    warnings = sum(1 for i in result.issues if i.severity == "warning")
    ok = errors == 0 and (not strict or warnings == 0)

    if json_out:
        sys.stdout.write(
            json.dumps(
                {
                    "ok": ok,
                    "path": to_posix(target),
                    "spec_version": data.meta.spec_version or None,
                    "project": data.meta.project or None,
                    "errors": errors,
                    "warnings": warnings,
                    "issues": [_issue_to_dict(i) for i in result.issues],
                }
            )
            + "\n"
        )
    else:
        sys.stdout.write(
            f"AgentPress lint: {to_posix(target)} (spec v{data.meta.spec_version or '?'})\n"
        )
        if errors == 0 and warnings == 0:
            sys.stdout.write("  ✓ valid\n")
        else:
            for issue in result.issues:
                icon = "✗" if issue.severity == "error" else "⚠"
                loc = ".".join(p for p in (issue.section, issue.key) if p)
                loc_s = f"[{loc}] " if loc else ""
                sys.stdout.write(f"  {icon} {issue.severity:<7} {loc_s}{issue.message}\n")
        sys.stdout.write(f"  {errors} error(s), {warnings} warning(s)\n")

    if errors > 0:
        return EXIT.ERRORS_FOUND
    if strict and warnings > 0:
        return EXIT.STRICT_OR_INTERNAL
    return EXIT.OK
