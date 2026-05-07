# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/repl/REPLServerSetupHistoryOptions`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-repl-server-setup-history-options --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify receipt contains interface, properties, and defaults

Review gate: Pass if receipt contains exact interface, properties, and defaults; fail if generic or missing

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
