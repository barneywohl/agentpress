# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/util/DebugLoggerFunction`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-debug-logger-function --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify no SOURCE FACT REQUIRED placeholders remain in the output.

Review gate: Pass if the material kit contains zero SOURCE FACT REQUIRED placeholders and the utility command executes without error.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
