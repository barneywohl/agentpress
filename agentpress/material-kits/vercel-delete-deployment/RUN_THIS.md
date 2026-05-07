# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/deployments/delete-a-deployment`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-delete-deployment --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains the exact endpoint, auth, and status code

Review gate: Kit must contain the exact DELETE endpoint, exact auth headers, and exact success status code with no invented claims

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
