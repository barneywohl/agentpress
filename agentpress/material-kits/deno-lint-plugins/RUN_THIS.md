# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://docs.deno.com/runtime/reference/lint_plugins/`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/deno-lint-plugins --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify lint plugin fields are present and valid.

Review gate: Pass if material kit contains exact plugin API signatures, configuration options, and lifecycle hooks with no missing fields.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
