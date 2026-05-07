# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Runtime/CustomPreview/bindRemoteObjectFunctionId`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-bindremoteobjectfunctionid --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the compact context contains the extracted method signature and return type

Review gate: The compact context must contain the exact method signature, imports, and return type from the source document, with no invented details

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
