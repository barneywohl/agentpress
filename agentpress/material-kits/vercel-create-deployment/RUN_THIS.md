# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/deployments/create-a-new-deployment`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-create-deployment --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains the exact endpoint, required fields, and auth format.

Review gate: Kit must contain the exact Vercel endpoint path, all required fields, and the auth format before approval.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
