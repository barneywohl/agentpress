# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Profiler/CoverageRange/startOffset`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-startoffset --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-startoffset --json and verify receipt fields are populated

Review gate: Material kit manifest exists at agentpress/material-kits/bun-startoffset/material-manifest.json with all required fields populated

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
