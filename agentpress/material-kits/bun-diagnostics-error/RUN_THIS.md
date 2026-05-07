# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/diagnostics_channel/TracingChannelCollection/error`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-diagnostics-error --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error 'bun install/runtime failure' --json and confirm the kit passes with no missing SOURCE FACT REQUIRED placeholders.

Review gate: Pass if the material kit contains no SOURCE FACT REQUIRED placeholders after source fact extraction; fail if any remain.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
