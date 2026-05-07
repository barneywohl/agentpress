# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/EventData/TestEnqueue/column`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-column --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and confirm receipt shows compact context for Bun column with exact API endpoint, JSON schema, and status codes extracted from source doc.

Review gate: Pass if receipt shows compact context for Bun column with exact API endpoint, JSON schema, and status codes extracted from source doc. Fail if receipt shows generic or missing content.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
