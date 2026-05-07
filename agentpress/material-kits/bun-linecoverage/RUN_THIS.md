# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/RunOptions/lineCoverage`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-linecoverage --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the bun-linecoverage material kit appears with no errors.

Review gate: Pass if the material kit contains the exact lineCoverage property name, data type, and default value from the source doc.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
