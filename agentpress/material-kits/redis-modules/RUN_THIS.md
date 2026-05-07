# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/bdbs/modules`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-modules --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm no SOURCE FACT REQUIRED placeholders remain in the llms_slice.

Review gate: Pass if the material-manifest.json contains at least 3 concrete source facts about Redis modules with no placeholders; fail if any SOURCE FACT REQUIRED placeholders remain.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
