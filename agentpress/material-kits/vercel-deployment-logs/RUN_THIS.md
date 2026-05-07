# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/logs/get-logs-for-a-deployment`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-deployment-logs --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the material-manifest.json file was created at agentpress/material-kits/vercel-deployment-logs/material-manifest.json with all required fields populated

Review gate: Material kit contains SOURCE FACT REQUIRED placeholders for all source-specific claims; no invented endpoint names, status codes, or response shapes

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
