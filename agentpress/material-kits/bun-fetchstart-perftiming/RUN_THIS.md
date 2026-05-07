# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/perf_hooks/PerformanceResourceTiming/fetchStart`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-fetchstart-perftiming --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-fetchstart-perftiming --json and verify receipt contains compact context for fetchStart performance timing

Review gate: Pass if the material kit contains compact, citation-ready context for the Bun fetchStart performance timing that agents can use without reading the full documentation

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
