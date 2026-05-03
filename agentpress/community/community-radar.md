# AgentPress Community Radar

Public agent-builder watering holes and painpoints.

## Top findings
- **stale or non-executable docs/commands** → required docs command lint gate
- **unsafe or unclear permissions before tool execution** → policy/permission manifest per command
- **tool discovery/configuration friction** → MCP-compatible static tool catalog export
- **runtime reproducibility and flaky environments** → environment fingerprint + reproducible run bundle
- **agent-to-agent trust, identity, and governance** → agent identity card + signed capability policy

## Sources
- [Cline](https://github.com/cline/cline) — human-in-loop approval, MCP tool ecosystem, terminal/browser/file edits
- [Roo Code](https://github.com/RooCodeInc/Roo-Code) — multi-mode agents, custom modes, BYO model/API routing
- [OpenHands](https://github.com/All-Hands-AI/OpenHands) — sandbox reliability, browser/test loops, install friction
- [AutoGen](https://github.com/microsoft/autogen) — agent-to-agent governance, identity/policy enforcement, tool integrations
- [CrewAI](https://github.com/crewAIInc/crewAI) — pre-execution validation, memory/storage backends, multi-agent orchestration
- [LangChain / LangGraph](https://github.com/langchain-ai/langchain) — agent observability, tool calling contracts, state graphs
- [LlamaIndex](https://github.com/run-llama/llama_index) — RAG freshness, citations, connectors
- [Hacker News agent-builder threads](https://hn.algolia.com/?q=AI%20coding%20agents) — skepticism about flaky agents, E2E self-debug, package/source search MCP
- [r/LocalLLaMA and related coding-agent threads](https://www.reddit.com/r/LocalLLaMA/search/?q=coding%20agent%20MCP) — local model cost/privacy, context windows, tool reliability
- [MCP servers/directories](https://github.com/modelcontextprotocol/servers) — tool discovery, safe permissions, server quality
