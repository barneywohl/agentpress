# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Runtime/ConsoleAPICalledEventDataType/timestamp`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-timestamp --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the kit passes with no errors and the manifest file exists at agentpress/material-kits/bun-timestamp/material-manifest.json

Review gate: The material kit must contain SOURCE FACT REQUIRED placeholders for property name, type, parent object, and valid values, and must not contain invented or hallucinated details.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
