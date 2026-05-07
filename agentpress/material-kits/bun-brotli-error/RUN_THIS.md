# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/zlib/constants/BROTLI_DECODER_ERROR_FORMAT_CONTEXT_MAP_REPEAT`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-brotli-error --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the kit contains the exact error code, zlib constant, and decoder context without SOURCE FACT REQUIRED placeholders remaining.

Review gate: Pass if the kit contains the exact error code, zlib constant, and decoder context; fail if any SOURCE FACT REQUIRED placeholders remain.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
