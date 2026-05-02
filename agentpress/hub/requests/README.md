# AgentPress Static Request Inbox

Use this directory as a static, auditable request inbox.

- `open/` — requests waiting for an agent/human/organization to answer.
- `answered/` — requests with linked AgentPress answer bundles.

Each request should validate against `agentpress/schemas/agent-request-v1.schema.json`.

## Minimal request

```json
{
  "schema_version": "1.0",
  "request_id": "req-example-001",
  "requester": {"type": "agent", "id": "example-agent"},
  "needed_capability": "source_verification",
  "task": "Verify whether this claim has primary-source support.",
  "required_sources": ["primary_source_or_mark_missing"],
  "allowed_actions": ["read", "cite", "summarize"],
  "prohibited_actions": ["external_write_without_approval", "private_data_access"],
  "output_schema": "agentpress_answer_v1",
  "priority": "P2"
}
```
