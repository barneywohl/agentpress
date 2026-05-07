# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/sqlite/DatabaseSync/loadExtension`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-sqlite-loadextension --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-sqlite-loadextension --validate to verify the material kit contains valid method signature, extension path, and error handling information.

Review gate: Material kit must contain valid Bun SQLite loadExtension method signature, extension path requirements, and error handling information that agents can use to load SQLite extensions without runtime errors.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
