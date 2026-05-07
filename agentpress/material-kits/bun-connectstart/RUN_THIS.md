# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/globals/PerformanceResourceTiming/connectStart`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-connectstart --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify bun-connectstart kit passes with all SOURCE FACT REQUIRED placeholders filled

Review gate: Kit must contain exact property names, exact types, and exact return shapes with no SOURCE FACT REQUIRED placeholders remaining

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
