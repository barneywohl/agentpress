# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/oss_and_stack/stack-with-enterprise/deprecated-features/triggers-and-functions/concepts/library_configuration`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-library-configuration --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the compact context card contains the Redis library configuration parameters

Review gate: The material kit contains the exact Redis library configuration parameters, their types, and validation rules, not generic Redis documentation

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
