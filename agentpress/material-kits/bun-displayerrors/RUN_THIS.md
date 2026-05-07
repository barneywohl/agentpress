# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/vm/RunningCodeInNewContextOptions/displayErrors`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-displayerrors --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the receipt shows successful materialization with compact context for the Bun displayErrors option.

Review gate: Pass if the material kit contains compact, citation-ready context for the Bun displayErrors option that prevents runtime error handling failures from missing or misunderstood displayErrors options. Fail if the kit is generic or missing source-specific facts.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
