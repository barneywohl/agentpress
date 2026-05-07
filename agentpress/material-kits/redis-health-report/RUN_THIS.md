# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/crdb/health_report`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-health-report --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify receipt shows SOURCE FACT REQUIRED placeholders filled with actual source facts, not placeholder text.

Review gate: Pass if material-manifest.json contains SOURCE FACT REQUIRED placeholders that are filled with real source facts after extraction; fail if placeholders remain unfilled or contain generic text.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
