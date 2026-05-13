"""Top-level entry point for the AgentPress v1.0 Python CLI.

Mirrors bin/agentpress.js exactly: same verbs, same flags, same exit codes,
same JSON output schemas. Both CLIs use their respective core parser
package (`@agent_press/core` for Node, `agentpress-core` for Python).
"""
from __future__ import annotations

import sys

from . import _exit_codes as EXIT
from ._doctor import run_doctor
from ._init import run_init
from ._legacy import run_legacy
from ._lint import run_lint
from ._receipt import run_receipt
from ._version import __version__


_TOP_HELP = f"""AgentPress v{__version__} — agents.txt for any repo

Usage: agentpress <command> [options]

Commands:
  init        Drop an agents.txt at your repo root in under a minute.
  lint        Validate an agents.txt against the v1.0 spec.
  doctor      Run a health check on your repo's v1.0 surface.
  receipt     Generate a content-addressed proof receipt.
  legacy      Forward to the v0.x command surface (deprecation banner).

Options:
  -h, --help          Show this help.
  -v, --version       Print version ({__version__}).

Docs: https://github.com/barneywohl/agentpress
Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md
"""

_VERBS = {
    "init": run_init,
    "lint": run_lint,
    "doctor": run_doctor,
    "receipt": run_receipt,
    "legacy": run_legacy,
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not args or args[0] in ("-h", "--help"):
        sys.stdout.write(_TOP_HELP)
        return EXIT.OK
    if args[0] in ("-v", "--version"):
        sys.stdout.write(__version__ + "\n")
        return EXIT.OK

    cmd, *rest = args
    fn = _VERBS.get(cmd)
    if fn is None:
        sys.stderr.write(f"Unknown command '{cmd}'. See `agentpress --help`.\n")
        return EXIT.ERRORS_FOUND

    try:
        return fn(rest)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"Internal error: {exc}\n")
        import os
        if os.environ.get("AGENTPRESS_DEBUG") == "1":
            import traceback
            traceback.print_exc()
        else:
            sys.stderr.write("(set AGENTPRESS_DEBUG=1 for stack trace)\n")
        return EXIT.STRICT_OR_INTERNAL


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
