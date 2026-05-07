# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/customize/extensions/authentication-api-debugger-extension`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-debugger-extension --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains the exact installation steps, API endpoints, and callback URL configuration from the source documentation.

Review gate: The kit must contain the exact installation steps, API endpoints, and callback URL configuration from the source documentation, with no invented steps or endpoints.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
