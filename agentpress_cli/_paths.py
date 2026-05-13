"""Cross-platform path helpers. Mirrors bin/lib/paths.js."""
from __future__ import annotations

import os
from pathlib import Path


def resolve_agents_txt(arg: str | None) -> Path:
    """Resolve the agents.txt path from a user-supplied argument.

    Rules:
      - undefined/None → CWD/agents.txt
      - existing directory → <arg>/agents.txt
      - else → arg as-is (treated as a file)
    Always absolute.
    """
    cwd = Path.cwd()
    if not arg:
        return (cwd / "agents.txt").resolve()
    candidate = (cwd / arg).resolve()
    if candidate.is_dir():
        return candidate / "agents.txt"
    return candidate


def find_repo_root(start: Path | None = None) -> Path | None:
    """Walk up the directory tree to find a `.git` ancestor."""
    cur = Path(start or Path.cwd()).resolve()
    while True:
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent


def root_or_cwd(start: Path | None = None) -> Path:
    return find_repo_root(start) or Path(start or Path.cwd()).resolve()


def write_file_atomic(target: Path, content: str, encoding: str = "utf-8") -> None:
    """Atomic write: temp file in the same dir + rename. Cross-platform."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f".{target.name}.tmp-{os.getpid()}"
    tmp.write_text(content, encoding=encoding)
    tmp.replace(target)


def to_posix(p: Path | str) -> str:
    """Normalise a path to forward slashes for JSON / receipt interoperability."""
    return str(p).replace(os.sep, "/")
