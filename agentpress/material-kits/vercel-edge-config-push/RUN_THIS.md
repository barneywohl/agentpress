# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/marketplace/push-data-into-a-user-provided-edge-config`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-edge-config-push --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit passes without errors and the proof receipt fields are populated.

Review gate: Kit must contain SOURCE FACT REQUIRED placeholders for the API endpoint, auth headers, and request body shape before any source-specific claims are added.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
