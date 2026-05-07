# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/EventData/Error/name`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-eventdata-error-name --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-eventdata-error-name --validate and confirm the receipt shows the kit was created with proper context budget and validation passed.

Review gate: The material kit must contain compact, citation-ready context for Bun: name that prevents agents from encountering unresolved errors, and the proof receipt must confirm the kit passed validation.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
