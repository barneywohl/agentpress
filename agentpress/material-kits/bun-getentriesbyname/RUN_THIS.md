# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/perf_hooks/PerformanceObserverEntryList/getEntriesByName`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-getentriesbyname --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error 'bun install/runtime failure' --json and verify the kit contains SOURCE FACT REQUIRED fields for method signature, parameters, and return shape

Review gate: Kit must contain SOURCE FACT REQUIRED placeholders for method signature, required parameters, and return shape before source facts are extracted

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
