# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/api/myorganization/idp-management/refresh-provisioning-configuration-attribute-mapping`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-refresh-provisioning-attribute-mapping --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the kit passes with no errors and the proof receipt shows all source facts extracted.

Review gate: Pass if the kit contains the exact attribute field names, mapping schema, and refresh endpoint behavior from the source document. Fail if the kit contains generic or placeholder content.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
