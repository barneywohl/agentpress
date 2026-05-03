# AgentPress Queue Adapter Kit

Static/local durable queue adapter contract for workflow agents.

```bash
python3 scripts/agentpress.py queue-adapter-kit --json
```

Includes message schema, retry/backoff policy, idempotency key rules, health export, and dead-letter semantics. No external broker write is performed.
