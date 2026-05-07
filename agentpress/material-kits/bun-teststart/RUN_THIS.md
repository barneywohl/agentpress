# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/EventData/TestStart`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-teststart --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict to verify the card contains specific API properties, event data structure, and test lifecycle hooks

Review gate: Card must contain at least 3 specific SOURCE FACT REQUIRED placeholders for unverified claims, real API properties, and no generic filler text

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
