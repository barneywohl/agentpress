# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/crypto/DecipherChaCha20Poly1305/_transform`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-crypto-transform --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the kit passes without errors and the proof receipt is logged.

Review gate: Pass if the kit contains SOURCE FACT REQUIRED placeholders for all un-verified claims, and the utility_command uses the real AgentPress CLI without invented commands.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
