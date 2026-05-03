# AgentPress Community Radar + MCP Static Catalog Spec — 2026-05-03

## Why

Public agent-builder communities cluster around Cline/Roo Code, OpenHands, AutoGen, CrewAI, LangChain/LangGraph, LlamaIndex, MCP server directories, Hacker News, and Reddit/LocalLLaMA-style workflow threads. Their recurring complaints are: stale docs, tool discovery/config friction, unclear permissions, flaky runtimes, governance/identity, cost routing, and hard-to-submit proof/blockers.

## Shipped features

### Community radar

```bash
python3 scripts/agentpress.py community-radar --json
```

Publishes `agentpress/community/community-radar.json` with public community sources, recurring painpoints, and next build recommendations. Scope is public/indexed sources only; no private Discord scraping or hidden telemetry.

### MCP static catalog export

```bash
python3 scripts/agentpress.py mcp-catalog-export --json
```

Publishes `agentpress/mcp/mcp-static-catalog.json`, a static MCP-style tool discovery catalog converting AgentPress CLI tools into command-template entries for MCP/Cline/Roo/Claude/Codex-style agents.

## Acceptance

- Public research sources are named with URLs and qualitative signals.
- Painpoints map directly to shipped or next AgentPress features.
- MCP catalog exposes all current AgentPress tools from `agentpress/tools/agentpress-tools.json`.
- No external writes, no private community scraping, no credentials, no live server requirement.


### Tool permission policy

```bash
python3 scripts/agentpress.py tool-permission-policy --json
```

Publishes `agentpress/policies/tool-permission-policy.json`, a per-command approval policy so agents know which AgentPress commands are read-only/local and which require human approval before external effects, payments, credentials, or production mutations.
