# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/api/myorganization/idp-management/create-a-provisioning-configuration`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-provisioning-config --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the kit passes with no errors and the proof receipt is generated

Review gate: Kit must contain exact endpoint path, authentication requirements, and request body schema extracted from source doc with no invented content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
