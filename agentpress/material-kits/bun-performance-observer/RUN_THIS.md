# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/globals/PerformanceObserver`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-performance-observer --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit passes with no errors and the receipt shows the exact constructor, observe method, and entry types

Review gate: Kit must contain exact constructor signature, observe method parameters, and performance entry types from the source doc with no invented details

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
