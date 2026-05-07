# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Runtime/EvaluateParameterType`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-evaluate-parameter-type --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify returned JSON has no errors and material-manifest.json exists at agentpress/material-kits/bun-evaluate-parameter-type/material-manifest.json

Review gate: Material-manifest.json exists at correct path with valid JSON containing SOURCE FACT REQUIRED placeholders for enum values, parameter signatures, and return types

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
