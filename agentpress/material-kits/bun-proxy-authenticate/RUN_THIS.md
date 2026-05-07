# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/http2/IncomingHttpHeaders/proxy-authenticate`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-proxy-authenticate --json`.

Validation/proof: Run: python3 scripts/agentpress.py proof-receipt --kit bun-proxy-authenticate --claim 'Proxy authentication configured successfully'

Review gate: Pass if the kit contains the exact HTTP headers, authentication callback, and expected status codes from the source documentation.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
