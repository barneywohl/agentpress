# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/http2/Http2ServerEventMap/sessionError`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-sessionerror --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget agentpress/material-kits/bun-sessionerror/material-manifest.json --json --strict and verify the manifest contains correct source facts

Review gate: Pass if the material-manifest.json contains SOURCE FACT REQUIRED placeholders for error type, error signature, and error handling; fail if it contains generic or invented content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
