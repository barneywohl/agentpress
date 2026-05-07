# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/http2/ServerStreamFileResponseOptionsWithError/onError`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-onerror --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-onerror --field onError_response_shape to verify the proof receipt captures the exact response shape.

Review gate: Pass if the proof receipt captures the exact onError response shape, error codes, and error types. Fail if the proof receipt is empty or contains placeholder values.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
