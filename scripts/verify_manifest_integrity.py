#!/usr/bin/env python3
"""Verify AgentPress manifest integrity pointers.

Fail closed if .well-known/agentpress.json advertises a sha256 for llms.txt
that does not match the checked-out llms.txt. This keeps the machine-readable
trust contract honest before publish/deploy.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LLMS = ROOT / "llms.txt"
MANIFEST = ROOT / ".well-known" / "agentpress.json"

actual = "sha256-" + hashlib.sha256(LLMS.read_bytes()).hexdigest()
manifest = json.loads(MANIFEST.read_text())
expected = manifest.get("integrity", {}).get("llms_txt_sha256")

if expected != actual:
    raise SystemExit(
        json.dumps(
            {
                "ok": False,
                "error": "llms.txt integrity mismatch",
                "expected": expected,
                "actual": actual,
            },
            indent=2,
        )
    )

print(json.dumps({"ok": True, "llms_txt_sha256": actual}, indent=2))
