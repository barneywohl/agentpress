# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/http2/IncomingHttpHeaders/proxy-authorization`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-proxy-authorization --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify that the material kit contains no SOURCE FACT REQUIRED placeholders remaining and that the header name, auth token, and response shape are concrete and valid.

Review gate: Pass if the material kit contains no SOURCE FACT REQUIRED placeholders and the header name, auth token, and response shape are concrete and valid for the Bun proxy authorization endpoint.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
