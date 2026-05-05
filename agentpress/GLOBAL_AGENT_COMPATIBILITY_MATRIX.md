# Global Agent Compatibility Matrix

Status meanings: **green** = local/static proof exists; **amber** = usable static contract but no native/live adapter; **roadmap** = not implemented.

| Agent family | Status | Current AgentPress surface | Proof command / evidence | Limits / next connector work |
|---|---|---|---|---|
| Search crawler | green | `sitemap.xml`, `robots.txt`, `.well-known/agentpress.json` | `python3 scripts/validate_agentpress_assets.py` | Keep URLs fresh after site changes. |
| RAG indexer | green | `llms.txt`, `agentpress/agent-instructions.json`, schemas | `python3 scripts/check_agentpress_positioning.py` | Add richer source-map deltas for large repos. |
| Browser agent | green | `index.html`, static docs, approval boundaries | `python3 scripts/agentpress.py browser-smoke --json --require-json` | Live browser proof is environment-dependent. |
| Claude / Claude Code | green | static adapter docs + CLI proof commands | `python3 scripts/agentpress.py compatibility-matrix --runtime claude --json` | Native `claude-init` generation is P2 roadmap. |
| GPT / Codex | green | `agentpress/adapters/codex/`, `llms.txt`, CLI gates | `python3 scripts/agentpress.py compatibility-matrix --runtime codex --json` | Keep first-run docs copy-paste safe. |
| Cursor / Cline / Roo | amber | static manifests and permission policy | `python3 scripts/agentpress.py tool-permission-policy --json` | Native IDE/extension config writers must remain opt-in. |
| MCP-style consumers | amber | `agentpress/mcp/mcp-static-catalog.json` | `python3 scripts/agentpress.py mcp-catalog-export --json` | Static catalog only; no live stdio/SSE server until `agentpress mcp-serve` lands. |
| LangChain / LangGraph | amber | native adapter skeleton + SDK docs | `python3 scripts/agentpress.py native-adapter-check --json` | Add tested loader package examples. |
| CrewAI | amber | native adapter skeleton + command templates | `python3 scripts/agentpress.py native-adapter-check --json` | Add live crew tool wrapper proof. |
| OpenHands | amber | native adapter skeleton + proof commands | `python3 scripts/agentpress.py native-adapter-check --json` | Add host transcript proof. |
| LlamaIndex | amber | native adapter skeleton + RAG surfaces | `python3 scripts/agentpress.py native-adapter-check --json` | Add tested reader/loader. |
| Live MCP server | roadmap | none | n/a | Implement and test `agentpress mcp-serve`; do not claim current live server support. |

Packaging note: npm `0.2.0-rc.2` is local metadata for the next approved publish; PyPI may remain at `0.2.0rc1` until a separate approved PyPI release.
