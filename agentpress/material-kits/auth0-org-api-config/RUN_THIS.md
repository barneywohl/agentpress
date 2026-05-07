# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/api/myorganization/config/get-my-organization-api-configuration`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-org-api-config --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit auth0-org-api-config --validate to verify the material kit contains valid endpoint, authentication, and response shape information.

Review gate: Material kit must contain valid Auth0 organization API configuration endpoint, authentication requirements, and response shape information that agents can use to configure organizations without misconfiguring OAuth/OIDC flows.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
