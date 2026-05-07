# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/perf_hooks/PerformanceResourceTiming/responseStart`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-responsestart-perftiming --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the extracted facts match the source doc

Review gate: Pass if extracted facts are source-accurate and no invented claims; fail if SOURCE FACT REQUIRED placeholders remain unfilled

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
