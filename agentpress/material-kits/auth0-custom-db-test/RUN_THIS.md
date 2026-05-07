# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/authenticate/database-connections/custom-db/test-custom-database-connections`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-custom-db-test --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit auth0-custom-db-test --claim 'test-connection-success' and verify receipt shows SOURCE FACT REQUIRED specific success payload

Review gate: Pass if material-manifest.json contains SOURCE FACT REQUIRED placeholders for endpoint, status code, and configuration parameters; fail if placeholders are missing or filled with non-source content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
