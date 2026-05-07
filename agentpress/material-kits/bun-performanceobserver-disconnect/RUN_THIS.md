# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/globals/PerformanceObserver/disconnect`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-performanceobserver-disconnect --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and confirm compact kit card generated with SOURCE FACT REQUIRED placeholders filled

Review gate: Kit card contains exact disconnect() method signature, exact error cases, and exact return type — no generic placeholders

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
