# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/api/myorganization/config/get-identity-provider-configuration`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-identity-provider-config --json`.

Validation/proof: Run: python3 scripts/agentpress.py context-budget agentpress/material-kits/auth0-identity-provider-config --json --strict and confirm the proof receipt shows a valid material-manifest.json with all required fields populated.

Review gate: Pass if the material-manifest.json exists at the specified path and contains valid JSON with the expected fields. Fail if the file is missing or contains invalid JSON.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
