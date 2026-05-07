# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/deployments/cancel-a-deployment`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-cancel-deployment --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the kit was created with correct Vercel deployment cancellation details.

Review gate: Pass if the material kit contains the exact Vercel cancel deployment endpoint path, auth headers, and error codes from the source doc. Fail if generic or missing source facts.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
