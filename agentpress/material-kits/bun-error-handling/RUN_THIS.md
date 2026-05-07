# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/https/ServerEventMap/error`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-error-handling --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error 'bun install/runtime failure' --json and verify the receipt shows all SOURCE FACT REQUIRED items filled with real source facts, no remaining placeholders.

Review gate: Pass if the material kit contains zero remaining SOURCE FACT REQUIRED placeholders after source fact extraction; fail if any placeholders remain.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
