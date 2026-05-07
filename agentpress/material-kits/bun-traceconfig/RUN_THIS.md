# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/NodeTracing/TraceConfig`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-traceconfig --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the compact context card contains exact config fields, exact types, and exact validation rules with no generic placeholders.

Review gate: Pass if the material-manifest.json contains exact config fields, exact types per field, and exact validation rules — all SOURCE FACT REQUIRED placeholders must be resolved with real data from the target doc.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
