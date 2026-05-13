"""Interactive prompts. Mirrors bin/lib/prompts.js."""
from __future__ import annotations

import sys


def ask(question: str, default: str | None = None) -> str:
    hint = f" [{default}]" if default else ""
    sys.stderr.write(f"? {question}{hint}: ")
    sys.stderr.flush()
    try:
        answer = input().strip()
    except EOFError:
        return default or ""
    return answer or (default or "")


def ask_yes_no(question: str, default_yes: bool = True) -> bool:
    hint = "[Y/n]" if default_yes else "[y/N]"
    while True:
        sys.stderr.write(f"? {question} {hint}: ")
        sys.stderr.flush()
        try:
            a = input().strip().lower()
        except EOFError:
            return bool(default_yes)
        if a == "":
            return bool(default_yes)
        if a in {"y", "yes", "1", "true"}:
            return True
        if a in {"n", "no", "0", "false"}:
            return False
