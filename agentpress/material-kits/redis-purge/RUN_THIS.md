# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/crdbs/purge`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-purge --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit passes with zero errors and the proof receipt shows SOURCE FACT REQUIRED placeholders were filled

Review gate: Kit must contain exact request body schema, exact authentication headers, and exact response codes from the source document with no invented content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
