# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Debugger/ScriptFailedToParseEventDataType/startLine`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-debugger-startline --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains no SOURCE FACT REQUIRED placeholders after source fact extraction

Review gate: Kit must contain zero SOURCE FACT REQUIRED placeholders after source fact extraction, and must contain valid Bun startLine debug steps with no missing fields

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
