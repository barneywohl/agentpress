# AgentPress MCP Static Catalog

Static MCP-style export for agents that discover tools through catalogs instead of prose.

```bash
python3 scripts/agentpress.py mcp-catalog-export --json
```

This is read-only/static discovery; it does not start a server or grant credentials.

## Does this start a live MCP server?

No. This directory is a static contract/reference surface: JSON resources, command templates, side-effect notes, and approval boundaries that MCP-style agents can ingest. It does not open stdio/SSE, mutate MCP host config, grant credentials, or register tools dynamically.

Roadmap: `agentpress mcp-serve` may become a real local MCP server in a future release. Until that command exists and is documented with tests, describe AgentPress as **static MCP-style discovery**, not a live MCP server.
