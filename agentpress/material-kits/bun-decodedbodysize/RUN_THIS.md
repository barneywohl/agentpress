# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/globals/PerformanceResourceTiming/decodedBodySize`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-decodedbodysize --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify receipt shows valid decodedBodySize metric with SOURCE FACT REQUIRED placeholders filled

Review gate: Kit must contain SOURCE FACT REQUIRED placeholders for type definition, numeric range, and access path before source facts are extracted

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
