# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/globals/ConsoleOptions/ignoreErrors`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-ignore-errors --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the material-manifest.json contains correct ignoreErrors schema

Review gate: Pass if the material-manifest.json contains SOURCE FACT REQUIRED placeholders for unverified claims about ignoreErrors behavior

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
