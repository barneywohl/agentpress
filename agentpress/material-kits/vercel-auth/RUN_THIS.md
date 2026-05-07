# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/vercel-sandbox/concepts/authentication`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-auth --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the material-kit contains at least 3 exact environment variable names and at least 1 exact callback URL pattern from the source document

Review gate: The material-kit must contain at least 3 exact environment variable names, at least 1 exact callback URL pattern, and at least 1 exact authentication provider name from the source document, with no invented names or patterns

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
