# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/bun/SQL/PostgresOrMySQLOptions/database`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-database --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify receipt shows compact database endpoint context with no missing fields

Review gate: Pass if receipt shows compact citation-ready database context; fail if generic or missing endpoint details

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
