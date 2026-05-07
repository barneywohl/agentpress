# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/globals/PerformanceMeasure/startTime`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-starttime-performance --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the material-manifest.json contains valid performance timing entries

Review gate: Material kit contains actionable performance timing details, not just generic runtime documentation

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
