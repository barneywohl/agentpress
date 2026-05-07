# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/api/management/v2/actions/post-deploy-draft-version`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-post-deploy-draft-version --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the compact context card cites the exact endpoint, request schema, and authentication requirements without hallucination

Review gate: Pass if the compact context card cites the exact endpoint path, required request body schema, and authentication scopes without hallucinating or omitting critical details

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
