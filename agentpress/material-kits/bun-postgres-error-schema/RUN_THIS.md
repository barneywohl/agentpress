# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/bun/SQL/PostgresError/schema`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-postgres-error-schema --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-postgres-error-schema --claim 'schema-validation-success' and verify receipt shows SOURCE FACT REQUIRED specific error payload

Review gate: Pass if material-manifest.json contains SOURCE FACT REQUIRED placeholders for error fields, error codes, and error response shape; fail if placeholders are missing or filled with non-source content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
