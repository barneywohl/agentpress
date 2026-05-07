# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/authenticate/protocols/saml/saml-configuration/deprovision-users-in-saml-integrations`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-saml-deprovision --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains no SOURCE FACT REQUIRED placeholders after source fact extraction

Review gate: Kit must contain zero SOURCE FACT REQUIRED placeholders after source fact extraction, and must contain valid Auth0 SAML deprovisioning steps with no missing fields

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
