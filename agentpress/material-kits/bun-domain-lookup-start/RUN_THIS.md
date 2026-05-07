# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/globals/PerformanceResourceTiming/domainLookupStart`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-domain-lookup-start --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify all SOURCE FACT REQUIRED placeholders are filled with real data.

Review gate: Pass if all SOURCE FACT REQUIRED placeholders are filled with verified source facts; fail if any placeholder remains unfilled.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
