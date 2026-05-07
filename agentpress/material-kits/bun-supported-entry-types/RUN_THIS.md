# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/globals/PerformanceObserver/supportedEntryTypes`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-supported-entry-types --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the material kit passes the budget check with extracted entry types present

Review gate: The material kit must contain SOURCE FACT REQUIRED placeholders for at least three specific entry types and at least two specific performance metrics before the builder can proceed past the quality gate

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
