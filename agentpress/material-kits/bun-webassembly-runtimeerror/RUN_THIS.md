# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/bun/WebAssembly/RuntimeError`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-webassembly-runtimeerror --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the kit passes with no errors and the manifest contains the extracted source facts

Review gate: The material kit must contain the exact RuntimeError class name, the exact error properties and methods, and the exact error codes as extracted from the source document, with no invented fields or assumptions

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
