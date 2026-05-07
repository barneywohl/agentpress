# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/EventData/TestEnqueue/nesting`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-test-nesting --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-test-nesting --json and verify receipt shows nesting API method, configuration, and error handling extracted.

Review gate: Pass if material kit contains compact nesting context with SOURCE FACT REQUIRED placeholders filled; fail if generic or missing source facts.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
