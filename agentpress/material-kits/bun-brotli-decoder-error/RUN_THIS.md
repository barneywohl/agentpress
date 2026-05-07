# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/zlib/constants/BROTLI_DECODER_ERROR_FORMAT_RESERVED`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-brotli-decoder-error --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and confirm the kit was created with correct Bun error details.

Review gate: Pass if the material kit contains the exact Bun BROTLI_DECODER_ERROR_FORMAT_RESERVED error meaning, trigger conditions, and resolution steps from the source doc. Fail if generic or missing source facts.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
