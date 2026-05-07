# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/zlib/constants/BROTLI_DECODER_ERROR_FORMAT_PADDING_2`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-brotli-decoder-error-format-padding-2 --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-brotli-decoder-error-format-padding-2 --json and verify the receipt shows the kit was generated with the correct source facts.

Review gate: The material kit must contain the exact BROTLI_DECODER_ERROR_FORMAT_PADDING_2 constant name, its numeric value, and the exact error scenario extracted from the source document, with no invented or guessed values.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
