# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/stream/default/Transform/[asyncIterator]`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-async-iterator --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm compact context budget passes with SOURCE FACT items extracted

Review gate: Pass if material-manifest.json exists at agentpress/material-kits/bun-async-iterator/ with validated SOURCE FACT items for method signatures, return types, and error patterns

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
