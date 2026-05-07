# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/deployments/upload-deployment-files`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-upload-deployment-files --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit passes with zero errors and the proof receipt is logged

Review gate: Pass if the material kit contains exact Vercel API endpoint, request schema, and authentication method; fail if any SOURCE FACT REQUIRED placeholder remains unfilled

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
