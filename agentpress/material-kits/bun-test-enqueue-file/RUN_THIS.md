# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/EventData/TestEnqueue/file`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-test-enqueue-file --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-test-enqueue-file --claim 'Bun file API documented with SOURCE FACT REQUIRED for method name, SOURCE FACT REQUIRED for parameter types, SOURCE FACT REQUIRED for return shape' and verify the receipt shows the source facts were extracted correctly.

Review gate: Pass if the material kit contains the exact method name, parameter types, and return shape extracted from the source document. Fail if any SOURCE FACT REQUIRED placeholders remain unfilled.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
