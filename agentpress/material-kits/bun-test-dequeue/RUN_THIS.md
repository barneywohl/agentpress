# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/TestsStreamEventMap/test:dequeue`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-test-dequeue --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains test:dequeue commands, test runners, and test configurations

Review gate: Kit must contain SOURCE FACT REQUIRED placeholders for test:dequeue commands, test runners, and test configurations; kit must not contain invented commands

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
