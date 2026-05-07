# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/edge-config/get-edge-config-items`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-edge-config-items --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit builds without errors

Review gate: Kit builds successfully, contains SOURCE FACT REQUIRED placeholders for source-specific claims, and does not contain generic filler

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
