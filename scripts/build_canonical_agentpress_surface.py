#!/usr/bin/env python3
"""Build canonical AgentPress public discovery surfaces without legacy archive noise."""
from __future__ import annotations

from pathlib import Path
import datetime
import json

BASE = "https://barneywohl.github.io/agentpress"
RAW = "https://raw.githubusercontent.com/barneywohl/agentpress/refs/heads/main"
ROOT = Path(__file__).resolve().parents[1]

ALLOW_EXACT = {
    "", "index.html", "README.md", "AGENTS.md", "llms.txt", "robots.txt", "sitemap.xml", "openapi.yaml", "metadata.json", ".nojekyll",
    ".well-known/agentpress.json", ".well-known/ai-ingestion.json", ".well-known/ai-plugin.json",
}
ALLOW_PREFIXES = (
    "agentpress/",
    "agentpress_cli/",
    "scripts/agentpress.py",
    "scripts/validate_agentpress_assets.py",
    "scripts/check_agentpress_availability.py",
    "scripts/check_agentpress_positioning.py",
    "scripts/build_canonical_agentpress_surface.py",
    "pyproject.toml",
)
DENY_PARTS = {".git", "__pycache__"}
DENY_PREFIXES = (
    "legacy/", "dataset/", "datasets/", "discovery/evals/korea", "query-pages/", "ticker-theses/", "rag-pack/", "productized-funnel/",
    "platform-packs/", "share-kit/", "locales/", "seo/", "telemetry/", "growth-system/", "forum-packs/", "ai-forums/",
)

def include(path: str) -> bool:
    if path in ALLOW_EXACT:
        return True
    if any(path.startswith(prefix) for prefix in DENY_PREFIXES):
        return False
    return any(path.startswith(prefix) for prefix in ALLOW_PREFIXES)

def kind(path: str) -> str:
    if path.endswith((".json", ".jsonl", ".yaml", ".yml", ".xml", ".opml", ".cff", ".txt")):
        return "machine_manifest_or_data"
    if path.endswith((".md", ".html")):
        return "human_and_agent_readable_page"
    if path.endswith((".py", ".js", ".sh")):
        return "script_or_tool"
    return "asset"

def main() -> int:
    paths: list[str] = []
    for f in ROOT.rglob("*"):
        if not f.is_file() or any(part in DENY_PARTS for part in f.parts) or f.name == ".DS_Store":
            continue
        rel = f.relative_to(ROOT).as_posix()
        if include(rel):
            paths.append(rel)
    paths = sorted(set(paths))
    url_paths = [""] + paths
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{BASE + ('/' + p if p else '/')}</loc></url>\n" for p in url_paths)
        + "</urlset>\n",
        encoding="utf-8",
    )
    assets = [
        {"path": p, "github_pages_url": f"{BASE}/{p}", "raw_githubusercontent_url": f"{RAW}/{p}", "kind": kind(p)}
        for p in paths
    ]
    payload = {
        "schema_version": "2026-05-02.agentpress-canonical-assets.v1",
        "name": "AgentPress canonical asset manifest",
        "canonical_product": "AgentPress",
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "purpose": "Clean public inventory for agents, crawlers, RAG systems, eval harnesses, MCP-style agents, and coding agents.",
        "canonical_pages": f"{BASE}/",
        "canonical_repo": "https://github.com/barneywohl/agentpress",
        "raw_base": f"{RAW}/",
        "primary_entrypoints": [
            "llms.txt",
            ".well-known/agentpress.json",
            ".well-known/ai-ingestion.json",
            "agentpress/articles/article-index.json",
            "agentpress/articles/article-index.jsonl",
            "agentpress/AGENT_ARTICLE_DATABASE_SPEC.md",
            "agentpress/hub/AGENT_HUB.md",
            "agentpress/profiles/agentpress-reference-agent/agent-profile.json",
            "locales/locale-index.json",
            "agentpress/schemas/README.md",
            "agentpress/examples/universal-agent-reachability/AGENT_ENTRYPOINT.md",
            "sitemap.xml",
            "openapi.yaml",
            "AGENTS.md",
        ],
        "asset_count": len(assets),
        "assets": assets,
    }
    out = ROOT / "discovery/all-assets-manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"canonical assets: {len(assets)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
