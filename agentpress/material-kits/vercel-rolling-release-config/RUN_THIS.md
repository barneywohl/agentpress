# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/rolling-release/get-rolling-release-configuration`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-rolling-release-config --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify that the material kit contains no SOURCE FACT REQUIRED placeholders remaining and that the endpoint path, auth headers, and response shape are concrete and valid.

Review gate: Pass if the material kit contains no SOURCE FACT REQUIRED placeholders and the endpoint path, auth headers, and response shape are concrete and valid for the Vercel rolling release configuration endpoint.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
