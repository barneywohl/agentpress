# AgentPress Compatibility Matrix

This is the executable proof harness for agent runtime compatibility.

Run:

```bash
python3 scripts/agentpress.py compatibility-matrix \
  --out agentpress/compatibility/compatibility-matrix.json \
  --json
```

The harness emits machine-readable results for Codex, Claude, Gemini, GLM, browser-style agents, and RAG agents. For each runtime it verifies:

1. adapter quickstart generation and validation
2. standard AgentPress self-test
3. landing receipt generation
4. proof submission pack generation

`binary_present` records whether the runtime binary exists on the executing host. A runtime can still pass the AgentPress protocol harness even when its native CLI is absent; third-party compatibility should be upgraded from `self_verified` to `third_party_verified` only when run on that runtime's real host.

Current matrix: `compatibility-matrix.json`.

## Static-vs-live MCP note

AgentPress compatibility currently proves static manifests, CLI command templates, and local validation gates. MCP entries are static discovery contracts, not a running stdio/SSE MCP server.
