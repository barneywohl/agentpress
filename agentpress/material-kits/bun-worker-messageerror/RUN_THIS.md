# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/worker_threads/WorkerEventMap/messageerror`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-worker-messageerror --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-worker-messageerror --claim "Messageerror event handler documented with exact syntax and error properties" and verify the receipt shows all SOURCE FACT REQUIRED placeholders filled with source-specific facts.

Review gate: Pass if the material kit contains the exact event listener syntax, exact error object properties, and exact error handling patterns extracted from the source doc. Fail if any SOURCE FACT REQUIRED placeholder remains unfilled or contains generic/placeholder text.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
