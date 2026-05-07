# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Runtime/EvaluateReturnType/exceptionDetails`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-exception-details --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and confirm the kit passes validation without errors

Review gate: Kit must contain SOURCE FACT REQUIRED placeholders for all source-specific claims and must not contain any invented or assumed content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
