# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/bun/BuildConfig/splitting`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-splitting --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the manifest contains the extracted BuildConfig properties and splitting behavior

Review gate: Pass if the material-manifest.json contains the exact Bun BuildConfig properties, splitting behavior, and output patterns extracted from the source document

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
