# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Debugger/EvaluateOnCallFrameParameterType/generatePreview`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-generate-preview --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit passes the quality bar with no missing or invented fields.

Review gate: Pass if the material-manifest.json contains the exact method signature, parameters, and response shape from the source document, with no invented methods or parameters.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
