# AgentPress Mesh Discovery

AgentPress nodes can discover each other through static public URLs.

```bash
python3 scripts/agentpress.py discover https://barneywohl.github.io/agentpress/ \
  --registry agentpress/mesh/known-agents.json \
  --out /tmp/agentpress-discovery.json \
  --json
```

Discovery checks `llms.txt`, `.well-known/agentpress.json`, tool manifest, release index, contract feed, and search index. The registry is static JSON and can be mirrored, searched, or used by other agents to find tools/capabilities.
