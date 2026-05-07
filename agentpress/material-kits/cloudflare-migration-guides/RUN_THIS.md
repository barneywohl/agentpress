# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://developers.cloudflare.com/workers/testing/vitest-integration/migration-guides`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/cloudflare-migration-guides --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the material-manifest.json exists at agentpress/material-kits/cloudflare-migration-guides/material-manifest.json with non-empty fields

Review gate: The material-manifest.json must contain at least 3 concrete migration steps, at least 2 breaking changes, and at least 1 testing integration status field from the source

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
