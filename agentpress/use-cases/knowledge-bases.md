# Use AgentPress for Knowledge Bases

Reference bundle: [`../examples/agent-knowledge-sharing/`](../examples/agent-knowledge-sharing/)

Best for: help centers, docs portals, policy libraries, product knowledge, internal wikis.

Agents need:
- a single obvious entrypoint,
- source maps,
- mirror/localization policy,
- allowed transformations,
- citation rules,
- safe handoff instructions.

Run:

```bash
python3 scripts/agentpress.py validate agentpress/examples/agent-knowledge-sharing --json
python3 scripts/agentpress.py audit agentpress/examples/agent-knowledge-sharing --json
```
