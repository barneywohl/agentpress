# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/RunOptions/coverageIncludeGlobs`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-coverage-include-globs --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the material kit contains the exact coverageIncludeGlobs option name, glob pattern syntax, and RunOptions schema from the source documentation

Review gate: Pass if the material kit contains the exact coverageIncludeGlobs option name, exact glob pattern syntax, and exact RunOptions schema; fail if any source-specific detail is missing or replaced with generic placeholders

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
