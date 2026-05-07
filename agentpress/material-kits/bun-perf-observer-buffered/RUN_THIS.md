# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/perf_hooks/PerformanceObserverInit/buffered`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-perf-observer-buffered --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the proof receipt shows no SOURCE FACT REQUIRED placeholders remaining and the extracted facts match the source document

Review gate: Pass if the material kit contains zero SOURCE FACT REQUIRED placeholders after source fact extraction, and the extracted facts are verifiable against the source document at the target URL

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
