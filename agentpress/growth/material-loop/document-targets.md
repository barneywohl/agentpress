# AgentPress document-target distribution lane

Status: local/static, approval-gated. No external posting has occurred.

## Why these documents
These are public docs or material that autonomous coding agents already seek while setting up tools, MCP servers, runtimes, provider adapters, RAG/tool flows, and tool-calling schemas. The tactic is to make those materials easier to consume through AgentPress wrappers rather than pushing AgentPress as generic marketing.

## First document targets wrapped
| Kit | Audience | Target | Utility |
|---|---|---|---|
| `mcp-server-quickstart-docs` | MCP builders | https://modelcontextprotocol.io/docs/getting-started/intro | MCP config doctor |
| `openai-agents-sdk-tools-docs` | OpenAI Agents SDK users | https://openai.github.io/openai-agents-python/tools/ | provider/tool translation map |
| `anthropic-tool-use-docs` | Claude/tool-use builders | https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview | provider adapter repro pack |
| `langgraph-checkpoint-docs` | LangGraph agent teams | https://langchain-ai.github.io/langgraph/concepts/persistence/ | checkpoint replay repro |
| `openhands-runtime-docs` | OpenHands users | https://docs.all-hands.dev/ | discovery bridge |
| `cline-mcp-docs` | Cline MCP users | https://docs.cline.bot/mcp-servers/mcp | MCP config mutation guard |
| `roo-code-provider-docs` | Roo Code users | https://docs.roocode.com/ | provider adapter repro |
| `llamaindex-tools-docs` | LlamaIndex/RAG builders | https://docs.llamaindex.ai/en/stable/module_guides/deploying/agents/tools/ | context budget proof |
| `litellm-proxy-docs` | LiteLLM/proxy operators | https://docs.litellm.ai/docs/proxy/quick_start | provider error explainer |
| `vercel-ai-sdk-tools-docs` | AI SDK builders | https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling | provider/tool translation map |

## Execution rule
Use these kits internally first. External comments, PRs, DMs, or posts require Jake approval of the exact target and draft.

## Next proof step
Run each kit command locally where applicable, record success/blocker receipts, and promote the highest-signal two kits into approval packets.
