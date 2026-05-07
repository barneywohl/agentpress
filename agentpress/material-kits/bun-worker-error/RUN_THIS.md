# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/worker_threads/WorkerEventMap/error`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-worker-error --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the kit passes without errors and the proof receipt fields are populated.

Review gate: Kit must contain SOURCE FACT REQUIRED placeholders for the error event types, callback signatures, and error object properties before any source-specific claims are added.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
