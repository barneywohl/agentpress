# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/deployments/list-deployments`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-list-deployments --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the manifest contains the extracted endpoint, auth, and pagination facts

Review gate: Pass if the material-manifest.json contains the exact Vercel API endpoint path, required auth headers, and pagination parameters extracted from the source document

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
