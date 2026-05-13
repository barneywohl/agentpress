"""`agentpress init` — interactive wizard. Mirrors bin/lib/init.js."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

from agentpress_core import parse, validate

from . import _exit_codes as EXIT
from ._detect import detect_all
from ._paths import root_or_cwd, write_file_atomic, to_posix
from ._prompts import ask, ask_yes_no
from ._template import build_agents_txt, build_badge_snippet, build_github_workflow
from ._version import __version__


HELP = """Usage: agentpress init [path] [options]

Drop an agents.txt at the repo root, plus a GitHub Actions workflow that
validates it on every PR, plus a README badge snippet.

Options:
  -y, --non-interactive    Use sensible defaults; no prompts.
  -f, --force              Overwrite an existing agents.txt.
  -o, --out PATH           Write into PATH instead of the current repo root.
  -h, --help               Show this help.

Example:
  agentpress init
  agentpress init --non-interactive
  agentpress init ./my-project
"""


def uuid12() -> str:
    return secrets.token_hex(6)


def run_init(argv: list[str]) -> int:
    non_interactive = False
    force = False
    out: str | None = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--non-interactive", "-y"):
            non_interactive = True
        elif a in ("--force", "-f"):
            force = True
        elif a in ("--out", "-o"):
            i += 1
            out = argv[i] if i < len(argv) else None
        elif a in ("-h", "--help"):
            sys.stdout.write(HELP)
            return EXIT.OK
        elif not a.startswith("-"):
            out = a
        i += 1

    root = Path(out).resolve() if out else root_or_cwd()
    facts = detect_all(root)

    agents_txt_path = root / "agents.txt"
    if agents_txt_path.exists() and not force:
        sys.stderr.write(f"agents.txt already exists at {to_posix(agents_txt_path)}\n")
        sys.stderr.write("  Run `agentpress doctor` to check it, or pass --force to overwrite.\n")
        return EXIT.ERRORS_FOUND

    sys.stderr.write("AgentPress init\n")
    sys.stderr.write(f"  root: {to_posix(root)}\n")
    if facts["github_origin"]:
        gh = facts["github_origin"]
        sys.stderr.write(f"  detected: GitHub repo {gh['owner']}/{gh['repo']}\n")
    sys.stderr.write(f"  detected: {facts['repo_type']} project\n")
    if facts["ci"]:
        sys.stderr.write(f"  detected: CI = {facts['ci']}\n")
    sys.stderr.write("\n")

    if non_interactive:
        maintainer = facts["maintainer_email"] or "maintainer@example.com"
        disclose = True
        allow_prs = True
        protect_sensitive = True
        write_workflow = facts["ci"] == "github_actions"
    else:
        maintainer = ask("Maintainer email", facts["maintainer_email"] or "")
        disclose = ask_yes_no("AI disclosure required for agent-authored PRs?", True)
        allow_prs = ask_yes_no("Allow agents to file PRs without per-PR approval?", True)
        protect_sensitive = ask_yes_no(
            "Require human approval for changes to billing/, payments/, auth/, security/?", True
        )
        write_workflow = (
            ask_yes_no("Add a GitHub Action that lints agents.txt on every PR?", True)
            if facts["ci"] == "github_actions"
            else False
        )

    body = build_agents_txt(
        project=facts["project"],
        maintainer=maintainer,
        contact_for_agents=maintainer,
        ai_disclosure_required=disclose,
        allow_prs_without_approval=allow_prs,
        protect_sensitive_paths=protect_sensitive,
        repo_type=facts["repo_type"],
    )

    parsed = parse(body)
    val = validate(parsed)
    if not val.ok:
        sys.stderr.write("\nInternal error: generated agents.txt did not validate.\n")
        for issue in val.issues:
            if issue.severity == "error":
                sys.stderr.write(f"  - {issue.severity}: {issue.message}\n")
        return EXIT.STRICT_OR_INTERNAL

    write_file_atomic(agents_txt_path, body)
    wrote: list[Path] = [agents_txt_path]

    if write_workflow:
        wf_path = root / ".github" / "workflows" / "agentstxt.yml"
        if not wf_path.exists() or force:
            write_file_atomic(wf_path, build_github_workflow())
            wrote.append(wf_path)

    receipt_id = f"rcpt_{uuid12()}"
    receipt_path = root / "agentpress" / "receipts" / f"init_{receipt_id}.json"
    sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
    warns = sum(1 for issue in val.issues if issue.severity == "warning")
    receipt = {
        "schema_version": "agentpress-receipt.v1",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z",
        "kind": "init",
        "agents_txt_path": to_posix(agents_txt_path.relative_to(root)),
        "agents_txt_sha256": sha256,
        "spec_version": parsed.meta.spec_version,
        "project": parsed.meta.project,
        "validation": {"ok": True, "errors": 0, "warnings": warns},
        "agentpress_version": __version__,
        "receipt_id": receipt_id,
    }
    write_file_atomic(receipt_path, json.dumps(receipt, indent=2) + "\n")
    wrote.append(receipt_path)

    sys.stderr.write("\n")
    for w in wrote:
        sys.stderr.write(f"  ✓ wrote {to_posix(w.relative_to(root))}\n")
    sys.stderr.write("\n")
    sys.stderr.write("README badge snippet:\n\n")
    sys.stderr.write(f"  {build_badge_snippet(facts['github_origin'])}\n")
    sys.stderr.write("\n")
    sys.stderr.write(
        "Next: review agents.txt, commit, push. Tools that respect the standard will start respecting your contract.\n"
    )
    return EXIT.OK
