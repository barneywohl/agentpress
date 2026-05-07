# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/sdk/security/put-firewall-configuration`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-put-firewall-configuration --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the receipt shows the extracted facts

Review gate: Pass if the material-manifest.json contains the extracted facts; fail if it contains generic placeholders

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
