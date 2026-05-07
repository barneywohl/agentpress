# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/http2/constants/HTTP_STATUS_PROXY_AUTHENTICATION_REQUIRED`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-http-status-proxy-auth --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the HTTP status constant returns a valid response when triggered

Review gate: Pass if the material kit includes the exact HTTP status code number, description, response shape, and authentication requirements for the PROXY_AUTHENTICATION_REQUIRED constant; fail if any are missing or use placeholder values

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
