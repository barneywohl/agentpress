# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/v8/startupSnapshot/isBuildingSnapshot`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-isbuildingnapshot --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify no SOURCE FACT REQUIRED placeholders remain in the final kit

Review gate: Pass if the kit contains zero SOURCE FACT REQUIRED placeholders and all extracted facts match the source document; fail if any placeholders remain or facts are invented

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
