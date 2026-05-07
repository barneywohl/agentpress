# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/cluster/debuginfo`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-debuginfo --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the compact context card is generated with source facts filled in

Review gate: Pass if the material-manifest.json contains SOURCE FACT REQUIRED placeholders that are later filled with real facts from the source document; fail if generic claims without source specificity

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
