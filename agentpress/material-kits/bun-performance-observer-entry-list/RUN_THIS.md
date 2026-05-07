# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/globals/PerformanceObserverEntryList`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-performance-observer-entry-list --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm receipt shows compact context card with extracted method signatures, return types, and timing properties

Review gate: Pass if receipt confirms compact context card with extracted facts; fail if receipt shows missing or hallucinated facts

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
