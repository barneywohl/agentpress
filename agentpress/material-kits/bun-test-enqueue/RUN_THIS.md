# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/EventData/TestEnqueue`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-test-enqueue --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and confirm the kit contains the exact TestEnqueue method signature and configuration details.

Review gate: The kit must contain the exact TestEnqueue method signature, the exact parameters accepted, and the exact configuration or environment variables required for TestEnqueue to run without errors.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
