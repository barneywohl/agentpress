# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Runtime/SetCustomObjectFormatterEnabledParameterType/enabled`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-enabled --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt and verify receipt contains extracted preconditions, version constraints, and failure codes

Review gate: Material kit contains at least 3 extracted source facts with SOURCE FACT REQUIRED placeholders filled

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
