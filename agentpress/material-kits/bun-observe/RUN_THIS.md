# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/globals/PerformanceObserver/observe`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-observe --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-observe --validate and confirm receipt shows valid observation data returned

Review gate: Pass if the material kit contains exact method signatures, observer options, and entry types from the source document with no invented content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
