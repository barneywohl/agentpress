# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://docs.deno.com/runtime/reference/cli/install/`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/deno-install --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify all installation methods and commands are present

Review gate: Pass if material kit contains all installation methods, platform-specific commands, and setup steps from source doc

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
