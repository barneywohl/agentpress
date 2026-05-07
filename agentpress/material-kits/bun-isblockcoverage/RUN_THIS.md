# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Profiler/FunctionCoverage/isBlockCoverage`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-isblockcoverage --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the kit passes with zero errors and the proof receipt shows the source document was extracted correctly.

Review gate: Pass if the material kit contains the exact property name, parent object path, and return values from the source document. Fail if any SOURCE FACT REQUIRED placeholder remains unfilled.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
