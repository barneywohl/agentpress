# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Runtime/CallFunctionOnParameterType/arguments`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-inspector-arguments --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-inspector-arguments --claim 'inspector-arguments-available' --json and verify receipt shows valid status

Review gate: Pass if material-manifest.json exists at agentpress/material-kits/bun-inspector-arguments/material-manifest.json with valid slug, title, painpoint, utility_command, llms_slice, and proof_receipt_claim fields; fail otherwise.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
