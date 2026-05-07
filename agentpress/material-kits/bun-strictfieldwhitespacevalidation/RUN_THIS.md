# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/http2/SecureServerOptions/strictFieldWhitespaceValidation`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-strictfieldwhitespacevalidation --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and confirm receipt shows compact context generated for Bun strictFieldWhitespaceValidation option

Review gate: Material manifest contains SOURCE FACT REQUIRED placeholders for option name, configuration syntax, and error conditions; no invented claims

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
