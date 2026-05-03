# AgentPress Schemas

These are lightweight JSON Schema contracts for the required AgentPress bundle. They are intentionally stable, readable, and strict enough for CI validation without blocking useful prose.

Required machine-readable files:

- [`agent-task-card.schema.json`](./agent-task-card.schema.json)
- [`source-map.schema.json`](./source-map.schema.json)
- [`freshness.schema.json`](./freshness.schema.json)
- [`allowed-actions.schema.json`](./allowed-actions.schema.json)
- [`ai-ingestion.schema.json`](./ai-ingestion.schema.json)
- [`article-card.schema.json`](./article-card.schema.json)
- [`article-index.schema.json`](./article-index.schema.json)

Validation entrypoints:

```bash
python3 scripts/agentpress.py schema --json
python3 scripts/agentpress.py verify agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py fetch --base file://$PWD --out /tmp/agentpress-fetch --json
python3 scripts/agentpress.py index-articles
python3 scripts/validate_agentpress_assets.py
python3 scripts/check_agentpress_positioning.py
```

Follow the allowed-actions boundary and verify source claims before external use.
