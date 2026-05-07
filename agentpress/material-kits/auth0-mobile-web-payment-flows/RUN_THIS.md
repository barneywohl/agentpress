# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/authenticate/single-sign-on/native-to-web/configure-mobile-to-web-payment-flows`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-mobile-web-payment-flows --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains the extracted OAuth scopes, redirect URI patterns, and error codes from the source document

Review gate: The material kit must contain at least three concrete source facts from the Auth0 mobile-to-web payment flow documentation, with SOURCE FACT REQUIRED placeholders for any claims not yet extracted

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
