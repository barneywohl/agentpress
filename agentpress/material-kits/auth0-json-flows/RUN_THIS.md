# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/customize/forms/flows/integrations/json`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-json-flows --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the generated material-manifest.json contains the extracted JSON schema, endpoint paths, and callback structures.

Review gate: The material kit must contain the exact JSON schema structure, exact OAuth/OIDC endpoint paths, and exact callback URL structures as extracted from the source documentation, with no missing or incorrect information.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
