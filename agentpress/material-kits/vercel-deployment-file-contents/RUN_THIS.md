# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/deployments/get-deployment-file-contents`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-deployment-file-contents --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit vercel-deployment-file-contents --json and verify receipt fields are populated

Review gate: Material kit manifest exists at agentpress/material-kits/vercel-deployment-file-contents/material-manifest.json with all required fields populated

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
