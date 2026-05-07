# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/bun/BuildConfig/sourcemap`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-sourcemap --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and confirm the kit passes with no errors and the proof receipt is generated

Review gate: Kit must contain exact BuildConfig field name, supported types, and default behavior extracted from source doc with no invented content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
