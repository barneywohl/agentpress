# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/sdk/edge-config/create-an-edge-config`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-edge-config-create --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains extracted API endpoint, required fields, and authentication details

Review gate: Kit must contain exact API endpoint, exact HTTP method, exact required fields, and exact authentication method extracted from source document

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
