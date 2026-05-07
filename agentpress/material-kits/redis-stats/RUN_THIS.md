# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/bdbs/stats`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-stats --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the llms_slice contains no SOURCE FACT REQUIRED placeholders remaining after source fact extraction

Review gate: The material-manifest.json file exists at agentpress/material-kits/redis-stats/material-manifest.json and contains no SOURCE FACT REQUIRED placeholders in the llms_slice

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
