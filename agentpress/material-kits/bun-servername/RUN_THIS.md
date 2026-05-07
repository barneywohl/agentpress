# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/http2/SecureClientSessionOptions/servername`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-servername --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the compact context card contains the exact SecureClientSessionOptions parameter, type, and validation rules from the source document.

Review gate: The material kit must contain the exact SecureClientSessionOptions parameter, type, and validation rules from the source document, with no invented or assumed content.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
