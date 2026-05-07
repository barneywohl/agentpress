# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/edge-config/update-an-edge-config`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-edge-config-update --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit vercel-edge-config-update --claim "Edge config update endpoint documented with exact path, auth, and response shape" and verify the receipt shows all SOURCE FACT REQUIRED placeholders filled with source-specific facts.

Review gate: Pass if the material kit contains the exact endpoint path, exact request schema, and exact auth requirements extracted from the source doc. Fail if any SOURCE FACT REQUIRED placeholder remains unfilled or contains generic/placeholder text.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
