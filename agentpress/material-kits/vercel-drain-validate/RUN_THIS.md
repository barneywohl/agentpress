# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/sdk/drains/validate-drain-delivery-configuration`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-drain-validate --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit vercel-drain-validate --field 'configuration_endpoint' to verify the source fact extraction was successful.

Review gate: Pass if the material kit contains the exact Vercel drain delivery API endpoint path, the exact request body schema, the exact authentication headers, and the exact success response shape. Fail if any of these are missing or contain SOURCE FACT REQUIRED placeholders.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
