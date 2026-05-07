# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/EventData/TestDequeue`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-testdequeue --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and confirm the bun-testdequeue kit passes with zero errors and the llms_slice contains no SOURCE FACT REQUIRED placeholders remaining.

Review gate: The llms_slice must contain no SOURCE FACT REQUIRED placeholders after source fact extraction; all three fact categories must be filled with real data from the source document.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
