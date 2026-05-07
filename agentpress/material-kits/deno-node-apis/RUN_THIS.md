# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://docs.deno.com/runtime/reference/node_apis/`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/deno-node-apis --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify receipt shows SOURCE FACT REQUIRED fields populated with real Deno API data

Review gate: Material kit must contain SOURCE FACT REQUIRED placeholders that get filled with real Deno Node API compatibility data, not generic placeholder text

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
