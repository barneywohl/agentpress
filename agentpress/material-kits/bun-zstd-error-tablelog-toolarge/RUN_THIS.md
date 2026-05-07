# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/zlib/constants/ZSTD_error_tableLog_tooLarge`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-zstd-error-tablelog-toolarge --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify receipt shows all SOURCE FACT REQUIRED placeholders filled with extracted source facts

Review gate: Pass if material-manifest.json exists with populated source facts; fail if SOURCE FACT REQUIRED placeholders remain unfilled

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
