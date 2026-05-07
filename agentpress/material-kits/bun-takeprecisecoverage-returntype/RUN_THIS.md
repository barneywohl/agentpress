# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Profiler/TakePreciseCoverageReturnType`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-takeprecisecoverage-returntype --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the kit passes with zero failures and SOURCE FACT REQUIRED placeholders are resolved

Review gate: Kit must contain exact type definition, exact field structure, and exact coverage data shape with no invented data

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
