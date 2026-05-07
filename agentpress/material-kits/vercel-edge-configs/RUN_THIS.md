# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/edge-config/get-edge-configs`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-edge-configs --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit vercel-edge-configs --validate and confirm receipt shows valid configuration data returned

Review gate: Pass if the material kit contains exact endpoint paths, required parameters, and authentication details from the source document with no invented content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
