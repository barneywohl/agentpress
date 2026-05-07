# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/api/management/v2/actions/post-test-action`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-post-test-action --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit auth0-post-test-action --strict and verify receipt fields are populated

Review gate: Pass if kit contains compact, citation-ready context for Auth0 post-login actions that prevents OAuth/OIDC misconfiguration by autonomous agents

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
