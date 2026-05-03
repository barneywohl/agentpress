# AgentPress Queue Adapter Kit Spec — 2026-05-03

## Real feature

AgentPress now gives workflow agents a static/local durable queue contract: message schema, retry policy, idempotency keys, claim leases, health export, and dead-letter semantics.

## Command

```bash
python3 scripts/agentpress.py queue-adapter-kit --json
```

## Outputs

- `agentpress/queue/queue-message-schema.json`
- `agentpress/queue/retry-policy.json`
- `agentpress/queue/queue-message.example.json`
- `agentpress/queue/queue-health.example.json`
- `agentpress/queue/manifest.json`

## Safety

No external broker write, no credentials, no hidden queue. Static/local contract first.
