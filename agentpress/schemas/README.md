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

---

## Validation entrypoints

```bash
# List all schemas (machine-readable index)
python3 scripts/agentpress.py schema --json

# Validate a specific bundle directory
python3 scripts/agentpress.py verify agentpress/examples/api-docs-handoff --json

# Fetch from live site and validate
python3 scripts/agentpress.py fetch --base file://$PWD --out /tmp/agentpress-fetch --json

# Strict JSON Schema validation of a single contract file
python3 scripts/agentpress.py schema-validate <file> --schema <schema-name> --json

# Adversarial fixture suite (all broken bundles must fail)
python3 scripts/agentpress.py negative-fixtures --json

python3 scripts/agentpress.py index-articles
python3 scripts/validate_agentpress_assets.py
python3 scripts/check_agentpress_positioning.py
```

Follow the allowed-actions boundary and verify source claims before external use.

---

## CLI output keys

### `schema --json`
```json
{
  "schema_version": "2026-05-03.agentpress-cli-schema.v1",
  "canonical_base_url": "https://barneywohl.github.io/agentpress/",
  "count": 7,
  "schemas": [
    {
      "name": "agent_task_card",
      "file": "agent-task-card.schema.json",
      "url": "https://barneywohl.github.io/agentpress/agentpress/schemas/agent-task-card.schema.json",
      "local_path": "agentpress/schemas/agent-task-card.schema.json"
    }
  ]
}
```

### `verify <bundle> --json`
```json
{
  "status": "ok",
  "errors": [],
  "warnings": []
}
```

### `negative-fixtures --json`
```json
{
  "status": "ok",
  "count": 5,
  "passed": 5,
  "failed": 0
}
```

### `schema-validate <file> --schema <name> --json`
```json
{
  "schema_version": "2026-05-03.agentpress-strict-schema-validation.v1",
  "status": "ok",
  "file": "agentpress/agent-task-card.json",
  "schema": "agentpress/schemas/agent-task-card.schema.json",
  "validator": "agentpress_dependency_free_json_schema_subset",
  "errors": []
}
```

---

## Per-schema reference

### `agent-task-card.schema.json`

Required fields: `schema_version`, `title`, `task_type`, `target_agents`, `objective`, `input_contract`, `output_contract`, `allowed_actions`, `prohibited_actions`

Minimal valid example:
```json
{
  "$schema": "https://barneywohl.github.io/agentpress/agentpress/schemas/agent-task-card.schema.json",
  "schema_version": "2026-05-03.agentpress-task-card.v1",
  "title": "My Task",
  "task_type": "research",
  "target_agents": ["claude", "gpt-4o"],
  "objective": "Summarise the linked article and return structured JSON.",
  "input_contract": {"required": ["url"], "optional": ["max_tokens"]},
  "output_contract": {"required": ["summary", "citations"]},
  "allowed_actions": ["read_url", "extract_text"],
  "prohibited_actions": ["store_pii", "make_payments"]
}
```

---

### `freshness.schema.json`

Required fields: `schema_version`, `publication`, `generated_at`, `refresh_policy`, `default_freshness_window_days`

Minimal valid example:
```json
{
  "$schema": "https://barneywohl.github.io/agentpress/agentpress/schemas/freshness.schema.json",
  "schema_version": "2026-05-03.agentpress-freshness.v1",
  "publication": "My AgentPress Site",
  "generated_at": "2026-05-04T00:00:00Z",
  "refresh_policy": "regenerate weekly or on source change",
  "default_freshness_window_days": 7
}
```

Adversarial note: omitting `generated_at` causes `verify` to emit `freshness.json missing schema-required field: generated_at` and return non-zero. See `agentpress/fixtures/broken-bundles/freshness-missing-generated-at/`.

---

### `source-map.schema.json`

Required fields: `schema_version`, `publication`, `claims`

Each `claims` entry requires: `claim_id`, `claim`, `confidence`, `sources`. Each source requires: `title`, `url_or_path`.

Minimal valid example:
```json
{
  "$schema": "https://barneywohl.github.io/agentpress/agentpress/schemas/source-map.schema.json",
  "schema_version": "2026-05-03.agentpress-source-map.v1",
  "publication": "My AgentPress Site",
  "claims": [
    {
      "claim_id": "C001",
      "claim": "AgentPress validates agent task cards against JSON Schema.",
      "confidence": "high",
      "sources": [{"title": "AgentPress schemas README", "url_or_path": "agentpress/schemas/README.md"}]
    }
  ]
}
```

Adversarial note: omitting `claims` causes `verify` to emit `source-map.json missing schema-required field: claims`. See `agentpress/fixtures/broken-bundles/source-map-missing-claims/`.

---

### `allowed-actions.schema.json`

Required fields: `schema_version`, `allowed`, `requires_human_approval`, `prohibited`

Minimal valid example:
```json
{
  "$schema": "https://barneywohl.github.io/agentpress/agentpress/schemas/allowed-actions.schema.json",
  "schema_version": "2026-05-03.agentpress-allowed-actions.v1",
  "allowed": ["read_public_urls", "extract_text", "write_local_files"],
  "requires_human_approval": ["publish_to_npm", "push_to_github"],
  "prohibited": ["store_pii", "make_payments", "exfiltrate_data"]
}
```

Adversarial note: omitting `allowed-actions.json` entirely causes `verify` to emit `missing required file: allowed-actions.json`. See `agentpress/fixtures/broken-bundles/missing-allowed-actions/`.

---

### `ai-ingestion.schema.json` (`.well-known/ai-ingestion.json`)

Required fields: `schema_version`, `name`, `canonical_url`, `entrypoint`, `llms_txt`, `task_card`, `source_map`, `allowed_actions`, `citation_policy`, `disclaimer`

Minimal valid example:
```json
{
  "schema_version": "2026-05-03.agentpress-ai-ingestion.v1",
  "name": "My AgentPress Site",
  "canonical_url": "https://example.github.io/agentpress/",
  "entrypoint": "AGENT_ENTRYPOINT.md",
  "llms_txt": "llms.txt",
  "task_card": "agentpress/agent-task-card.json",
  "source_map": "agentpress/source-map.json",
  "allowed_actions": "agentpress/allowed-actions.json",
  "citation_policy": "agentpress/citation-policy.md",
  "disclaimer": "disclaimer.md"
}
```
