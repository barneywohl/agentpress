# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/zlib/constants/BROTLI_DECODER_ERROR_FORMAT_BLOCK_LENGTH_2`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-brotli-decoder-error-format-block-length-2 --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error 'bun install/runtime failure' --json and verify the kit passes with zero errors and the proof receipt is logged

Review gate: Pass if the material kit contains exact BROTLI_DECODER_ERROR_FORMAT_BLOCK_LENGTH_2 error code, message format, and recovery steps; fail if any SOURCE FACT REQUIRED placeholder remains unfilled

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
