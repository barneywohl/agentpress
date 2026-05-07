# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/crdbs/flush`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-flush --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the receipt shows the flush endpoint, request schema, and status codes were extracted.

Review gate: Pass if the material-manifest.json contains the exact Redis flush endpoint, request schema, and status codes from the source document. Fail if any field contains invented or generic content.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
