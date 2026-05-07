# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Debugger/EvaluateOnCallFrameParameterType/expression`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-expression --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the receipt shows all SOURCE FACT REQUIRED placeholders filled with real data from the source document

Review gate: The material-manifest.json must contain SOURCE FACT REQUIRED placeholders that are not yet filled, and the context-budget command must pass without errors

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
