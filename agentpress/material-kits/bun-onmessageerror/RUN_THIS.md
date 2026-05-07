# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/worker_threads/MessagePort/onmessageerror`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-onmessageerror --json`.

Validation/proof: Run: python3 scripts/agentpress.py context-budget . --json --strict and verify the material-manifest.json file contains no SOURCE FACT REQUIRED placeholders remaining.

Review gate: Pass if all SOURCE FACT REQUIRED placeholders are replaced with source-verified facts; fail if any placeholder remains.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
