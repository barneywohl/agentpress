# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/bun/WebAssembly/RuntimeError/stack`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-wasm-stack --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and confirm receipt shows compact context for Bun stack

Review gate: Pass if material-manifest.json exists at agentpress/material-kits/bun-wasm-stack/material-manifest.json with valid JSON

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
