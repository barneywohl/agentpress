# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/crdb/instance_info`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-instance-info --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the compact reference kit passes the quality gate with no errors.

Review gate: The compact reference kit must contain SOURCE FACT REQUIRED placeholders for the API endpoint, authentication headers, and JSON response schema, and must not contain any fabricated or hallucinated content.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
