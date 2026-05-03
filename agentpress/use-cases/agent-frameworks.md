# Use AgentPress for Agent Frameworks and Evals

Reference bundle: [`../examples/universal-agent-reachability/`](../examples/universal-agent-reachability/)

Best for: agent frameworks, eval harnesses, MCP-style systems, crawler/indexing tests, browser/coding agent compatibility.

Agents need:
- deterministic discovery paths,
- machine-readable contracts,
- executable fixtures,
- registry consistency,
- OpenAPI/local-asset parity,
- JSON CLI output for automation.

Run:

```bash
python3 scripts/agentpress.py doctor --json
python3 scripts/agentpress.py check-registry
python3 scripts/agentpress.py check-openapi
python3 scripts/agentpress.py eval agentpress/examples
```
