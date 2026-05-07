# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/http2/ClientSessionOptions/maxReservedRemoteStreams`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-maxreservedremotestreams --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the compact context card contains the Bun maxReservedRemoteStreams parameter details

Review gate: The material kit contains the exact Bun maxReservedRemoteStreams parameter details, its type, and validation rules, not generic Bun documentation

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
