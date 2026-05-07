# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/sign-in-with-vercel/authorization-server-api`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-authorization-server-api --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the material-manifest.json exists at agentpress/material-kits/vercel-authorization-server-api/material-manifest.json with valid JSON

Review gate: Material-manifest.json contains valid JSON with correct slug, title, and source facts extracted from the Vercel doc

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
