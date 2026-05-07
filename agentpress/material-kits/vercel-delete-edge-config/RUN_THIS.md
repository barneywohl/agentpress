# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/edge-config/delete-an-edge-config`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-delete-edge-config --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the compact context contains the exact endpoint, auth, and response shape.

Review gate: Pass if the compact context contains the exact endpoint, auth, and response shape without guessing.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
