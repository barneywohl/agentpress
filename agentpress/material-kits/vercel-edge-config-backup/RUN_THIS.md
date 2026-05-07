# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/edge-config/get-edge-config-backup`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-edge-config-backup --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the proof receipt shows no SOURCE FACT REQUIRED placeholders remaining and the extracted facts match the source document

Review gate: Pass if the material kit contains zero SOURCE FACT REQUIRED placeholders after source fact extraction, and the extracted facts are verifiable against the source document at the target URL

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
