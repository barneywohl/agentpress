# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/drains/validate-drain-delivery-configuration`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-drain-config --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the kit passes without errors

Review gate: Pass if the material-manifest.json contains the exact endpoint path, request body schema, and auth method extracted from the source document

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
