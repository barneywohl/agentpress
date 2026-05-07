# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Runtime/EvaluateParameterType/userGesture`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-user-gesture --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error 'bun install/runtime failure' --json and verify the kit passes with zero errors and the proof receipt shows 'userGesture API validated successfully'.

Review gate: Pass if the kit contains the exact inspector API endpoint, required parameters, and response shape extracted from the source doc. Fail if any SOURCE FACT REQUIRED placeholder remains unfilled.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
