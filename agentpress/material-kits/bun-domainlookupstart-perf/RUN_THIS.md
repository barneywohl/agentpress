# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/perf_hooks/PerformanceResourceTiming/domainLookupStart`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-domainlookupstart-perf --json`.

Validation/proof: Run: python3 scripts/agentpress.py context-budget agentpress/material-kits/bun-domainlookupstart-perf --json --strict and confirm the proof receipt shows a valid material-manifest.json with all required fields populated.

Review gate: Pass if the material-manifest.json exists at the specified path and contains valid JSON with the expected fields. Fail if the file is missing or contains invalid JSON.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
