# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/https/ServerOptions/ciphers`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-ciphers --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-ciphers --json and verify the receipt shows a valid material-manifest.json with all required fields populated.

Review gate: Pass if the material-manifest.json contains the exact Bun ciphers property, cipher string format, and default cipher list with SOURCE FACT REQUIRED placeholders filled after source fact extraction. Fail if the manifest contains generic or placeholder content without source-specific facts.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
