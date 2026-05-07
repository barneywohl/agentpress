# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/diagnostics_channel/TracingChannelCollection/start`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-start --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the material-manifest.json contains the extracted method signature, return value, and error conditions.

Review gate: Pass if the material-manifest.json contains the exact start() method signature, return value, and error conditions extracted from the source doc.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
