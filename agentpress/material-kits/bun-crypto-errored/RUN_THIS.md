# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/crypto/Cipheriv/errored`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-crypto-errored --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify no SOURCE FACT REQUIRED placeholders remain in the final card

Review gate: Card must have zero SOURCE FACT REQUIRED placeholders after extraction, and must pass package-registry-doctor validation

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
