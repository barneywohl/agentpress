# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/deployments/list-deployment-files`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-list-deployment-files --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit passes with no errors and the manifest file exists at agentpress/material-kits/vercel-list-deployment-files/material-manifest.json

Review gate: The material kit must contain SOURCE FACT REQUIRED placeholders for endpoint path, required parameters, authentication headers, and response shape, and must not contain invented or hallucinated details.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
