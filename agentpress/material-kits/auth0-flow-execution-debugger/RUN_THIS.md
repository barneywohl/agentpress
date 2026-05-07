# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/customize/forms/flows/flow-execution-and-debugger`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-flow-execution-debugger --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify that the material-manifest.json contains no SOURCE FACT REQUIRED placeholders and all fields contain specific extracted facts

Review gate: Material kit contains zero SOURCE FACT REQUIRED placeholders and all fields contain specific, extracted source facts with no generic or placeholder content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
