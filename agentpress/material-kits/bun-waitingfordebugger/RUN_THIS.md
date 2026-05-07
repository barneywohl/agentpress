# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/NodeWorker/AttachedToWorkerEventDataType/waitingForDebugger`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-waitingfordebugger --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the kit passes with no errors and the proof receipt shows all source facts extracted.

Review gate: Pass if the kit contains the exact waitingForDebugger event data type, inspector behavior, and debug session flow from the source document. Fail if the kit contains generic or placeholder content.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
