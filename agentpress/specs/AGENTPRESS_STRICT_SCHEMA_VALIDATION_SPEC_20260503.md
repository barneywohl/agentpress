# AgentPress Strict Schema Validation Spec — 2026-05-03

## Why

Required-field-only validation misses nested type drift and malformed contracts. Agents need fail-closed machine contracts before using bundles, submissions, receipts, permission policies, and tool catalogs.

## Commands

```bash
python3 scripts/agentpress.py schema-validate <file> --schema <schema-name-or-file> --json
python3 scripts/agentpress.py verify <bundle> --strict-schema --json
```

## Acceptance

- Dependency-free strict JSON Schema subset validator ships in `scripts/agentpress.py`.
- Valid fixture passes.
- Invalid fixture with wrong field type fails.
- `verify --strict-schema` applies strict schema validation to mapped bundle contracts.
- CI runs strict schema validation plus docs command lint as required gates.
