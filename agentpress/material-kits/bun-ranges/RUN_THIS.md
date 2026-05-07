# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Profiler/FunctionCoverage/ranges`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-ranges --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-ranges --validate to verify compact kit was created with proper source facts

Review gate: Kit contains SOURCE FACT REQUIRED placeholders for endpoint details, and compact context is present

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
