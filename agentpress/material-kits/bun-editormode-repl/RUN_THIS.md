# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/repl/REPLServer/editorMode`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-editormode-repl --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit budget is within acceptable range for the Bun ecosystem

Review gate: Pass if the material-manifest.json exists at agentpress/material-kits/bun-editormode-repl/material-manifest.json and contains valid Bun REPL editorMode configuration data with SOURCE FACT REQUIRED placeholders for source-specific claims

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
