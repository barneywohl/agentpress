#!/usr/bin/env python3
"""Fail if product-facing discovery files drift away from AgentPress positioning."""
from __future__ import annotations

from pathlib import Path
import sys

PRODUCT_FILES = [
    Path("index.html"),
    Path("llms.txt"),
    Path("metadata.json"),
    Path("discovery/search-query-map.md"),
    Path("discovery/agent-discovery-manifest.json"),
    Path("traffic/agent-traffic-map.json"),
    Path("traffic/agent-traffic-map.md"),
]

BANNED_PRIMARY_PHRASES = [
    "obsolete corpus",
    "obsolete traffic map",
    "obsolete research-agent framing",
    "obsolete all-assets manifest",
    "Build a Korea cheap-screen deletion agent",
]

REQUIRED_PHRASES = [
    "AgentPress",
]


def main() -> int:
    errors: list[str] = []
    for path in PRODUCT_FILES:
        if not path.exists():
            errors.append(f"missing product file: {path}")
            continue
        text = path.read_text(errors="replace")
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                errors.append(f"{path}: missing required phrase {phrase!r}")
        for phrase in BANNED_PRIMARY_PHRASES:
            if phrase in text:
                errors.append(f"{path}: banned primary-positioning phrase {phrase!r}")
    if errors:
        print("agentpress positioning check failed")
        for err in errors:
            print(f"- {err}")
        return 1
    print("agentpress positioning ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
