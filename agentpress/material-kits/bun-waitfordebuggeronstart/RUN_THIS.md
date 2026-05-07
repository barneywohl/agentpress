# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Target/SetAutoAttachParameterType/waitForDebuggerOnStart`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-waitfordebuggeronstart --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the kit passes with no errors

Review gate: Kit must contain specific Bun waitForDebuggerOnStart inspector details, not generic Bun documentation

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
