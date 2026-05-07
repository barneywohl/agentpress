# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/globals/PerformanceResourceTiming/startTime`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-starttime-perftiming --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the kit passes with no errors and the proof receipt claims match the extracted source facts

Review gate: Kit must contain exact property name, exact return type, and exact unit of measurement extracted from the source doc with no invented content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
