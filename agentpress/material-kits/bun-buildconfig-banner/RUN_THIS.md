# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/bun/BuildConfig/banner`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-buildconfig-banner --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the material-manifest.json file was created at agentpress/material-kits/bun-buildconfig-banner/material-manifest.json with all required fields populated

Review gate: Material kit contains SOURCE FACT REQUIRED placeholders for all source-specific claims; no invented property names, types, or configuration shapes

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
