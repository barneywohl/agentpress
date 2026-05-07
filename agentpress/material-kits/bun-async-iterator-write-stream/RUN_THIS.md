# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/tty/WriteStream/[asyncIterator]`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-async-iterator-write-stream --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and confirm the kit passes with no missing source facts and no unverified claims.

Review gate: The kit must contain the exact [asyncIterator] method signatures, exact return types, and exact error handling behavior extracted from the source doc, with no invented details.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
