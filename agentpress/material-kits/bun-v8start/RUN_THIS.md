# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/perf_hooks/PerformanceNodeTiming/v8Start`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-v8start --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the llms_slice contains no SOURCE FACT REQUIRED placeholders remaining after source fact extraction

Review gate: The material-manifest.json file exists at agentpress/material-kits/bun-v8start/material-manifest.json and contains no SOURCE FACT REQUIRED placeholders in the llms_slice

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
