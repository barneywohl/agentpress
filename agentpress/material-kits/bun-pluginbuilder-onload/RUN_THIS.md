# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/bun/PluginBuilder/onLoad`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-pluginbuilder-onload --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the Bun onLoad callback signature, input parameters, and error handling are present without SOURCE FACT REQUIRED placeholders

Review gate: Pass if the material kit contains zero SOURCE FACT REQUIRED placeholders after source fact extraction; fail if any remain

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
