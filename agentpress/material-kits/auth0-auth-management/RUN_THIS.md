# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/customize/forms/flows/integrations/auth0`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-auth-management --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit auth0-auth-management --claim "Auth0 OAuth/OIDC endpoints and configuration parameters extracted" and verify receipt contains extracted facts

Review gate: Material kit contains specific OAuth/OIDC endpoints, tenant configuration parameters, and API rate limits from source document, with no generic or placeholder content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
