# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/edge-config/get-an-edge-config-item`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-edge-config-item --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the edge config item context is compact and citation-ready

Review gate: Pass if the edge config item context is compact, citation-ready, and prevents deploy failures from missing context

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
