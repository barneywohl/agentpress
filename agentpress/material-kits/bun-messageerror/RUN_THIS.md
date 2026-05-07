# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/worker_threads/MessagePortEventMap/messageerror`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-messageerror --json`.

Validation/proof: Run: python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and confirm no uncaught exceptions on valid error handling.

Review gate: Kit produces valid error handling when messageerror events occur, returns clear error on invalid error handling.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
