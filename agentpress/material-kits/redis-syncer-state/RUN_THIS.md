# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/bdbs/syncer_state`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-syncer-state --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit redis-syncer-state --validate to verify compact kit was created with proper source facts

Review gate: Kit contains SOURCE FACT REQUIRED placeholders for endpoint details, and compact context is present

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
