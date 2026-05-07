# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Runtime/CallArgument/unserializableValue`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-unserializable-value --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify receipt fields for unserializable value handling and error coverage are populated

Review gate: Pass if receipt shows valid unserializableValue type, error coverage, and runtime compatibility without missing fields

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
