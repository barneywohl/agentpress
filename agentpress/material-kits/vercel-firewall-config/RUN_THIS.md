# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/security/read-firewall-configuration`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-firewall-config --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the kit materializes without error and the proof receipt shows all SOURCE FACT REQUIRED placeholders filled.

Review gate: Pass if the material-manifest.json exists at agentpress/material-kits/vercel-firewall-config/material-manifest.json and the proof receipt shows all SOURCE FACT REQUIRED placeholders resolved with real data from the source document.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
