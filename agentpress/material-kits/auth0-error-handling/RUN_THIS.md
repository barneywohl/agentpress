# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/authenticate/database-connections/custom-db/error-handling`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-error-handling --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the material kit passes the budget check with extracted error codes present

Review gate: The material kit must contain SOURCE FACT REQUIRED placeholders for at least three specific error codes and at least two specific HTTP status codes before the builder can proceed past the quality gate

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
