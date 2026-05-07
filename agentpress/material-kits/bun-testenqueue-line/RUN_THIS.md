# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/EventData/TestEnqueue/line`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-testenqueue-line --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error 'bun install/runtime failure' --json and verify the material-manifest.json exists at agentpress/material-kits/bun-testenqueue-line/material-manifest.json with non-empty fields

Review gate: The material-manifest.json must contain at least 3 concrete TestEnqueue/line API fields, at least 2 breaking changes, and at least 1 testing integration status field from the source

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
