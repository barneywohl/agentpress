# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/functions/configuring-functions/memory`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-memory --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify memory config fields are present and valid.

Review gate: Pass if material kit contains exact memory limits, configuration options, and scaling behavior with no missing fields.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
