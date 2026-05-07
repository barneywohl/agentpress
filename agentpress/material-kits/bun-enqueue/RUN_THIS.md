# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/stream/web/ReadableByteStreamController/enqueue`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-enqueue --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and confirm compact context is generated

Review gate: Pass if compact citation-ready context for Bun enqueue is produced without generic filler

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
