#!/usr/bin/env python3
# Minimal AgentPress consumer demo: fetch, parse, and decide next action.
import json
import urllib.request

BASE = "https://agentpress.pages.dev/"
for rel in ["llms.txt", ".well-known/agentpress.json", ".well-known/ai-ingestion.json"]:
    url = BASE + rel
    req = urllib.request.Request(url, headers={"User-Agent": "agentpress-demo/0.1"})
    with urllib.request.urlopen(req, timeout=20) as r:
        body = r.read().decode("utf-8")
    print(f"FETCHED {rel}: {len(body)} bytes")
    if rel.endswith(".json"):
        parsed = json.loads(body)
        print("  keys:", ", ".join(sorted(parsed.keys())[:8]))
print("NEXT: run `agentpress lint . --json` on your own repo to make it agent-readable.")
