# AgentPress Mesh Discovery

AgentPress nodes can discover each other through static public URLs.

```bash
python3 scripts/agentpress.py discover https://barneywohl.github.io/agentpress/ \
  --registry agentpress/mesh/known-agents.json \
  --out /tmp/agentpress-discovery.json \
  --json
```

Discovery checks `llms.txt`, `.well-known/agentpress.json`, tool manifest, release index, contract feed, and search index. The registry is static JSON and can be mirrored, searched, or used by other agents to find tools/capabilities.

## Self-registration

An AgentPress node can add itself to a local mesh registry after its public machine surfaces are live:

```bash
python3 scripts/agentpress.py discover --self-register \
  --canonical-url https://barneywohl.github.io/agentpress/ \
  --agent-id agentpress-barneywohl \
  --registry agentpress/mesh/known-agents.json \
  --json
```

Self-registration records canonical URL, tool manifest URL, release URL, contract feed URL, discovered tools, release version, and trust tier. It is self-asserted until backed by landing receipts, self-tests, and third-party handoff receipts.

## First-contact audit

`first-contact-audit.json` records the public URLs a new autonomous agent should fetch first and the top remaining fixes surfaced by GLM/team review.
