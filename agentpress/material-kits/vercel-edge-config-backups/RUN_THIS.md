# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/edge-config/get-edge-config-backups`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-edge-config-backups --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit passes with zero budget violations and SOURCE FACT REQUIRED placeholders are resolved

Review gate: Kit must contain exact API endpoint, exact authentication requirements, and exact response shape with no invented data

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
