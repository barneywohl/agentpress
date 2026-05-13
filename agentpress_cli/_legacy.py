"""`agentpress legacy <cmd>` — forwarding to v0.x CLI. Mirrors bin/lib/legacy.js."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from . import _exit_codes as EXIT


_BANNER_SHOWN = False


def _show_banner_once() -> None:
    global _BANNER_SHOWN
    if _BANNER_SHOWN:
        return
    if os.environ.get("AGENTPRESS_LEGACY_QUIET") == "1":
        return
    sys.stderr.write(
        "\n[deprecation] You're using the legacy v0.x command surface via `agentpress legacy ...`.\n"
        "              Legacy commands stay supported through v1.x and will be removed in v2.0.\n"
        "              Set AGENTPRESS_LEGACY_QUIET=1 to silence this message.\n\n"
    )
    _BANNER_SHOWN = True


def _legacy_script() -> Path:
    # agentpress_cli/_legacy.py → ../scripts/agentpress.py
    return (Path(__file__).resolve().parent.parent / "scripts" / "agentpress.py").resolve()


def run_legacy(argv: list[str]) -> int:
    if not argv or argv[0] in ("--help", "-h"):
        _show_banner_once()
        try:
            result = subprocess.run([sys.executable, str(_legacy_script()), "--help"])
            return result.returncode
        except FileNotFoundError:
            sys.stderr.write("✗ legacy script not found.\n")
            return EXIT.STRICT_OR_INTERNAL
    _show_banner_once()
    try:
        result = subprocess.run([sys.executable, str(_legacy_script()), *argv])
        return result.returncode
    except FileNotFoundError:
        sys.stderr.write("✗ legacy script not found.\n")
        return EXIT.STRICT_OR_INTERNAL
