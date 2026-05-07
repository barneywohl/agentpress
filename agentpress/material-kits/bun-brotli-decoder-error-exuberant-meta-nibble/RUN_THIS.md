# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/zlib/constants/BROTLI_DECODER_ERROR_FORMAT_EXUBERANT_META_NIBBLE`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-brotli-decoder-error-exuberant-meta-nibble --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the bun-brotli-decoder-error-exuberant-meta-nibble kit passes with no errors.

Review gate: Pass if the material-manifest.json contains the correct Bun BROTLI_DECODER_ERROR_FORMAT_EXUBERANT_META_NIBBLE fields and the proof receipt shows successful validation.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
