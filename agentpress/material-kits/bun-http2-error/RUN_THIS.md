# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/http2/Http2SecureServerEventMap/error`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-http2-error --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-http2-error --field 'error_event' to verify the source fact extraction was successful.

Review gate: Pass if the material kit contains the exact Bun Http2SecureServerEventMap error event name, the exact error event payload shape, the exact error handling approach, and the exact error recovery steps. Fail if any of these are missing or contain SOURCE FACT REQUIRED placeholders.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
