# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/authenticate/protocols/saml/saml-sso-integrations/configure-auth0-saml-service-provider/configure-ssocircle-as-saml-identity-provider`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-saml-ssocircle --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the material-manifest.json contains valid SAML configuration entries

Review gate: Material kit contains actionable SAML configuration steps, not just generic auth documentation

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
