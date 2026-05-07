# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/functions/configuring-functions/runtime`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-runtime --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify all runtime types and config options are present

Review gate: Pass if material kit contains all runtime types, version numbers, and config options from source doc

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
