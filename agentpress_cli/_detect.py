"""Repo type + CI detection. Mirrors bin/lib/detect.js."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


def detect_repo_type(root: Path) -> str:
    hits: list[str] = []
    if (root / "package.json").exists():
        hits.append("node")
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        hits.append("python")
    if (root / "go.mod").exists():
        hits.append("go")
    if (root / "Cargo.toml").exists():
        hits.append("rust")
    if (root / "Gemfile").exists():
        hits.append("ruby")
    if (root / "composer.json").exists():
        hits.append("php")
    if not hits:
        return "generic"
    if len(hits) == 1:
        return hits[0]
    return "monorepo:" + "+".join(hits)


def detect_ci(root: Path) -> str | None:
    if (root / ".github" / "workflows").exists():
        return "github_actions"
    if (root / ".gitlab-ci.yml").exists():
        return "gitlab"
    if (root / ".circleci" / "config.yml").exists():
        return "circleci"
    if (root / "azure-pipelines.yml").exists():
        return "azure"
    return None


_GIT_ORIGIN_RE = re.compile(
    r"url\s*=\s*(?:https?://github\.com/|git@github\.com:)([^/\s]+)/([^.\s]+?)(?:\.git)?\s*$",
    re.MULTILINE,
)


def detect_github_origin(root: Path) -> dict | None:
    cfg_path = root / ".git" / "config"
    if not cfg_path.exists():
        return None
    try:
        cfg = cfg_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    m = _GIT_ORIGIN_RE.search(cfg)
    if m:
        return {"owner": m.group(1), "repo": m.group(2)}
    return None


def _safe_read_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def detect_maintainer_email(root: Path) -> str | None:
    pkg = _safe_read_json(root / "package.json")
    if pkg:
        author = pkg.get("author")
        if isinstance(author, str):
            m = re.search(r"<([^>]+)>", author)
            if m:
                return m.group(1)
            if "@" in author:
                return author.strip()
        elif isinstance(author, dict) and author.get("email"):
            return author["email"]
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            py = pyproject.read_text(encoding="utf-8")
            m = re.search(r'email\s*=\s*"([^"]+)"', py)
            if m:
                return m.group(1)
        except OSError:
            pass
    try:
        res = subprocess.run(
            ["git", "config", "user.email"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        email = res.stdout.strip()
        if email:
            return email
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def detect_project_name(root: Path) -> str:
    pkg = _safe_read_json(root / "package.json")
    if pkg and pkg.get("name"):
        return pkg["name"]
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            py = pyproject.read_text(encoding="utf-8")
            m = re.search(r'^\s*name\s*=\s*"([^"]+)"', py, re.MULTILINE)
            if m:
                return m.group(1)
        except OSError:
            pass
    origin = detect_github_origin(root)
    if origin:
        return origin["repo"]
    return root.name


def detect_all(root: Path) -> dict:
    return {
        "root": str(root),
        "project": detect_project_name(root),
        "repo_type": detect_repo_type(root),
        "ci": detect_ci(root),
        "github_origin": detect_github_origin(root),
        "maintainer_email": detect_maintainer_email(root),
    }
