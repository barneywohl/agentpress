# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/EventData/Error/cause`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-cause --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and confirm the error cause context is compact and citation-ready

Review gate: The material-manifest.json contains SOURCE FACT REQUIRED placeholders that are ready to be filled with real source facts from the Bun documentation

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
