# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Runtime/PropertyDescriptor/configurable`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-configurable --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget agentpress/material-kits/bun-configurable/material-manifest.json --json --strict and confirm the receipt

Review gate: The compact kit contains the exact property name, configurable behavior, and runtime impact for the configurable property descriptor

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
