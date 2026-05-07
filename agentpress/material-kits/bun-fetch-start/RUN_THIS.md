# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/globals/PerformanceResourceTiming/fetchStart`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-fetch-start --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the proof receipt shows all SOURCE FACT REQUIRED placeholders filled with extracted source facts.

Review gate: Pass if the material kit contains the exact Bun PerformanceResourceTiming property path, timing unit, and minimum Bun version extracted from the source document. Fail if any SOURCE FACT REQUIRED placeholder remains unfilled.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
