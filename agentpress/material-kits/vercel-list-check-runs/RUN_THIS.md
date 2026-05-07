# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/sdk/checks-v2/list-check-runs-for-a-deployment`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-list-check-runs --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the material-manifest.json was created with no SOURCE FACT REQUIRED placeholders remaining

Review gate: Material manifest contains zero SOURCE FACT REQUIRED placeholders and all extracted facts match the source document

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
