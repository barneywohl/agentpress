# Global Agent Compatibility Matrix

| Agent family | What it needs | AgentPress artifact | Status |
|---|---|---|---|
| Search crawler | crawl seeds + sitemap | `sitemap.xml`, `robots.txt`, registry | shipped |
| RAG indexer | compact docs + source map | `llms.txt`, `source-map.json`, JSON feed | shipped |
| Browser agent | agent fallback page + safe actions | `index.html`, `allowed-actions.json` | shipped |
| Coding agent | templates + CLI + schemas | `templates/`, `scripts/agentpress.py`, `schemas/` | shipped |
| Eval agent | prompts + rubric + score | `agent-task-card.json`, eval JSONL, `score` | shipped |
| API agent | OpenAPI paths | `openapi.yaml` | shipped |
| MCP-style agent | tool/resource manifest | `agentpress/protocols/mcp-manifest.json` | shipped |
| Multilingual agent | language/region hints | registry metadata + locale docs | partial |
| Compliance/safety agent | action/disclaimer/citation policy | `allowed-actions.json`, `citation-policy.md`, `disclaimer.md` | shipped |
