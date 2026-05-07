# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/rolling-release/delete-rolling-release-configuration`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-delete-rolling-release --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the Vercel rolling release delete endpoint is correctly called with proper authentication, correct project ID, and correct configuration ID, returning a verified success response

Review gate: Pass if the material kit contains the exact DELETE endpoint path, exact authentication headers, and exact request body shape from the Vercel documentation; fail if any of these are missing or contain SOURCE FACT REQUIRED placeholders

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
