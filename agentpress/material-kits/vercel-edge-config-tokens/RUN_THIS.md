# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/edge-config/get-all-tokens-of-an-edge-config`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-edge-config-tokens --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit passes with zero errors and the proof receipt shows 'edge config tokens listed successfully'.

Review gate: Pass if the kit contains the exact API endpoint, required headers, and response shape extracted from the source doc. Fail if any SOURCE FACT REQUIRED placeholder remains unfilled.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
