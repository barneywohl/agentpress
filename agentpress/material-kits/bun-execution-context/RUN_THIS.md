# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Runtime/CallFunctionOnParameterType/executionContextId`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-execution-context --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error 'bun install/runtime failure' --json and confirm the kit materializes without error and the proof receipt shows all SOURCE FACT REQUIRED placeholders filled.

Review gate: Pass if the material-manifest.json exists at agentpress/material-kits/bun-execution-context/material-manifest.json and the proof receipt shows all SOURCE FACT REQUIRED placeholders resolved with real data from the source document.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
