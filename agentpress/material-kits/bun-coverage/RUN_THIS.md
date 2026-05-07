# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/RunOptions/coverage`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-coverage --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains the exact coverage configuration options, output formats, and CLI commands from the source documentation.

Review gate: The kit must contain the exact coverage configuration options, output formats, and CLI commands from the source documentation, with no invented options or commands.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
