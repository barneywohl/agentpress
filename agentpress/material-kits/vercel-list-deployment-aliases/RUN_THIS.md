# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/aliases/list-deployment-aliases`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-list-deployment-aliases --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify receipt shows SOURCE FACT REQUIRED fields populated with real data

Review gate: Material kit must contain SOURCE FACT REQUIRED placeholders that get filled with real Vercel API endpoint data, not generic placeholder text

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
