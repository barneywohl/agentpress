# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/bdb/status`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-status --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --validate --kit redis-status --strict and verify SOURCE FACT REQUIRED placeholders are filled with real source facts

Review gate: Pass if: material-manifest.json exists at agentpress/material-kits/redis-status/material-manifest.json, proof receipt shows all SOURCE FACT REQUIRED placeholders filled with real source facts, and context-budget validation passed

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
