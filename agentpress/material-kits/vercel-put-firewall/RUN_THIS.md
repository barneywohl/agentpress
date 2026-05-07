# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/security/put-firewall-configuration`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-put-firewall --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit vercel-put-firewall --claim 'Firewall configuration endpoint documented with SOURCE FACT REQUIRED for endpoint path, SOURCE FACT REQUIRED for request schema, SOURCE FACT REQUIRED for auth requirements' and verify the receipt shows the source facts were extracted correctly.

Review gate: Pass if the material kit contains the exact endpoint path, request schema, and authentication requirements extracted from the source document. Fail if any SOURCE FACT REQUIRED placeholders remain unfilled.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
