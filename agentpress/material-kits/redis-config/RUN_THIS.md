# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/modules/config`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-config --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify redis-config kit passes with all SOURCE FACT REQUIRED placeholders filled

Review gate: Kit must contain exact config parameter names, exact defaults, and exact API shapes with no SOURCE FACT REQUIRED placeholders remaining

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
