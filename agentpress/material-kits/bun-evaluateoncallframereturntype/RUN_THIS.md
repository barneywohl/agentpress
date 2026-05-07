# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Debugger/EvaluateOnCallFrameReturnType`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-evaluateoncallframereturntype --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the proof receipt fields are populated.

Review gate: Pass if the material-manifest.json contains valid inspector type context slices with SOURCE FACT REQUIRED placeholders for source-specific claims.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
