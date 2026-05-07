# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/bun/BuildConfig/bytecode`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-bytecode --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-bytecode --json and verify receipt fields: BuildConfig_schema, configuration_options, output_format are populated with SOURCE FACT REQUIRED placeholders replaced by extracted facts.

Review gate: Pass if proof receipt shows all SOURCE FACT REQUIRED placeholders replaced with extracted source facts; fail if any placeholder remains unmodified.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
