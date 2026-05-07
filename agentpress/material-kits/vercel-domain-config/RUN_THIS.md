# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/domains/get-a-domain-s-configuration`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-domain-config --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit vercel-domain-config --json and verify receipt shows domain configuration endpoint, authentication, and response shape extracted.

Review gate: Pass if material kit contains compact domain configuration context with SOURCE FACT REQUIRED placeholders filled; fail if generic or missing source facts.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
