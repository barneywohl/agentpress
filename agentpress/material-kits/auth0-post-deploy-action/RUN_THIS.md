# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/api/management/v2/actions/post-deploy-action`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-post-deploy-action --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains the exact trigger event name, exact payload shape, and exact error codes from the source doc.

Review gate: The kit must contain the exact trigger event name, exact payload shape, and exact error codes from the source doc, with no invented claims.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
