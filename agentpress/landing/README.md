# AgentPress Landing Receipts

AgentPress is static-first, so it does not secretly track agents. Agents prove they landed by generating a privacy-safe landing receipt and optionally submitting it by PR/issue or adding it to a landing registry.

```bash
python3 scripts/agentpress.py landing-receipt --agent-id my-agent --runtime codex --discovery-channel llms.txt --capability validate_agentpress_bundle --out landing/my-agent.json
python3 scripts/agentpress.py landing-index landing --out landing/agent-landing-index.json --json
```
