# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/customize/forms/flows/integrations/http-request`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-http-request --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the output contains at least 3 endpoint URLs, 5 parameter definitions, and 2 callback schemas from the Auth0 HTTP request documentation.

Review gate: The material kit must contain at least 3 specific endpoint URLs, 5 parameter definitions with types, and 2 callback schemas extracted from the Auth0 HTTP request documentation. If any of these are missing, the kit is incomplete and must be re-extracted.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
