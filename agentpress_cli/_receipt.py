"""`agentpress receipt` — content-addressed proof receipt. Mirrors bin/lib/receipt.js."""
from __future__ import annotations

import hashlib
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

from agentpress_core import parse, validate

from . import _exit_codes as EXIT
from ._paths import resolve_agents_txt, root_or_cwd, to_posix, write_file_atomic
from ._version import __version__


HELP = """Usage: agentpress receipt [path] [options]

Generate a content-addressed JSON receipt proving an agents.txt was
validated. Future v1.1 will add ed25519 signing; v1.0 receipts are
unsigned but include a sha256 of the file body so the receipt can be
verified later by re-hashing.

Options:
  --stdout-only         Print receipt to stdout; do not write to disk.
  --out PATH            Write receipt to PATH (default: agentpress/receipts/<id>.json).
  --json                Also print the receipt to stdout (default when writing).
  -h, --help            Show this help.

Exit codes:
  0  receipt generated
  1  agents.txt has errors
  3  agents.txt not found
"""


def uuid12() -> str:
    return secrets.token_hex(6)


def run_receipt(argv: list[str]) -> int:
    json_to_stdout = True
    stdout_only = False
    path_arg: str | None = None
    out: str | None = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--stdout-only":
            stdout_only = True
        elif a in ("--out", "-o"):
            i += 1
            out = argv[i] if i < len(argv) else None
        elif a == "--json":
            json_to_stdout = True
        elif a in ("-h", "--help"):
            sys.stdout.write(HELP)
            return EXIT.OK
        elif not a.startswith("-"):
            path_arg = a
        i += 1

    target = resolve_agents_txt(path_arg)
    if not target.exists():
        sys.stderr.write(
            f"agents.txt not found at {to_posix(target)}. Run `agentpress init` to create one.\n"
        )
        return EXIT.FILE_NOT_FOUND

    body = target.read_bytes()
    data = parse(body.decode("utf-8", errors="replace"))
    result = validate(data)
    errors = sum(1 for i in result.issues if i.severity == "error")
    warnings = sum(1 for i in result.issues if i.severity == "warning")

    if errors:
        sys.stderr.write(
            f"agents.txt has {errors} error(s). Receipt requires a valid file. "
            f"Run `agentpress lint` to see details.\n"
        )
        return EXIT.ERRORS_FOUND

    root = root_or_cwd()
    receipt_id = f"rcpt_{uuid12()}"
    sha256 = hashlib.sha256(body).hexdigest()
    receipt = {
        "schema_version": "agentpress-receipt.v1",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z",
        "kind": "lint",
        "agents_txt_path": to_posix(target.relative_to(root)) if root in target.parents else to_posix(target),
        "agents_txt_sha256": sha256,
        "spec_version": data.meta.spec_version,
        "project": data.meta.project,
        "validation": {"ok": errors == 0, "errors": errors, "warnings": warnings},
        "agentpress_version": __version__,
        "receipt_id": receipt_id,
    }
    body_json = json.dumps(receipt, indent=2)

    if stdout_only:
        sys.stdout.write(body_json + "\n")
        return EXIT.OK

    out_path = (
        Path(out).resolve()
        if out
        else root / "agentpress" / "receipts" / f"{receipt_id}.json"
    )
    write_file_atomic(out_path, body_json + "\n")
    if json_to_stdout:
        sys.stdout.write(body_json + "\n")
    try:
        rel = out_path.relative_to(root)
        sys.stderr.write(f"✓ receipt written to {to_posix(rel)}\n")
    except ValueError:
        sys.stderr.write(f"✓ receipt written to {to_posix(out_path)}\n")
    return EXIT.OK
