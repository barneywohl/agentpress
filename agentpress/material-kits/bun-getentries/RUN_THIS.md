# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/perf_hooks/PerformanceObserverEntryList/getEntries`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-getentries --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-getentries --field 'return_shape' --json and verify the receipt contains the extracted method signature, return type, and performance entry types.

Review gate: The kit must contain the exact method signature, return type, and performance entry types for getEntries, extracted from the source document.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
