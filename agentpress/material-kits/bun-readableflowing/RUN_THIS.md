# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/http2/ClientHttp2Stream/readableFlowing`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-readableflowing --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the property name, return type, and conditions are present and correct.

Review gate: Pass if the property name, return type, and conditions are present and correct; fail if any SOURCE FACT REQUIRED placeholder remains unfilled.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
