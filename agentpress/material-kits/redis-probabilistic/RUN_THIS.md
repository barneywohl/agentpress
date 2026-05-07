# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/bdb/probabilistic`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-probabilistic --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify that SOURCE FACT REQUIRED placeholders are replaced with real facts.

Review gate: Pass if all SOURCE FACT REQUIRED placeholders are replaced with verified facts from the source doc; fail if any placeholder remains.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
