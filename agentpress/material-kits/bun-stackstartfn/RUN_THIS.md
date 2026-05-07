# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/assert/default/AssertionErrorOptions/stackStartFn`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-stackstartfn --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm compact context budget passes for Bun stackStartFn card.

Review gate: Pass if: compact context card exists with SOURCE FACT REQUIRED placeholders filled from source doc extraction, and context-budget validation passes.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
