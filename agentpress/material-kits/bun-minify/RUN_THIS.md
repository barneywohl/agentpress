# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/bun/BuildConfig/minify`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-minify --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains the exact minify config field name, exact boolean values, and exact error conditions from the source doc.

Review gate: The kit must contain the exact minify config field name, exact boolean values, and exact error conditions from the source doc, with no invented claims.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
