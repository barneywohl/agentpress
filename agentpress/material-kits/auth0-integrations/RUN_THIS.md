# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/customize/forms/flows/integrations`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-integrations --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the kit passes all quality gates without errors

Review gate: The material kit must contain at least 3 specific integration endpoint paths, at least 2 callback URL patterns, and at least 1 authentication flow sequence; if any are missing or contain SOURCE FACT REQUIRED placeholders, the kit fails review

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
