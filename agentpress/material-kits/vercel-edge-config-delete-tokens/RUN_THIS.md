# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/edge-config/delete-one-or-more-edge-config-tokens`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-edge-config-delete-tokens --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit vercel-edge-config-delete-tokens --field delete-token-response-shape and verify 200 status with SOURCE FACT REQUIRED response body

Review gate: Pass if the kit contains compact citation-ready context for the DELETE endpoint, authentication scope, and response shape; fail if generic or missing source facts

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
