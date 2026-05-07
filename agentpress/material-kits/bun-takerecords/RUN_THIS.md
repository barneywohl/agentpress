# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/perf_hooks/PerformanceObserver/takeRecords`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-takerecords --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains the exact method signature, parameters, and return shape.

Review gate: The kit must contain the exact takeRecords method signature, the exact parameters, and the exact return shape.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
