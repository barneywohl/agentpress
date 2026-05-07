# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/sdk/deployments/get-a-deployment-by-id-or-url`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-deployment-lookup --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit passes with no errors and the receipt shows the exact endpoint, auth method, and response shape

Review gate: Kit must contain exact API endpoint, authentication method, and response shape from the source doc with no invented details

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
