# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/authenticate/login/oidc-conformant-authentication/oidc-adoption-implicit-flow`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-oidc-implicit-flow --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit auth0-oidc-implicit-flow --validate and confirm the receipt shows the kit was created with proper context budget and validation passed.

Review gate: The material kit must contain compact, citation-ready context for OIDC implicit flow that prevents agents from misconfiguring flows, and the proof receipt must confirm the kit passed validation.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
