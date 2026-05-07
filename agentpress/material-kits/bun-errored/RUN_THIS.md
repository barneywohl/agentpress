# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/stream/default/Transform/errored`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-errored --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the material-manifest.json exists at agentpress/material-kits/bun-errored/material-manifest.json with valid JSON

Review gate: Material-manifest.json contains valid JSON with correct slug, title, and source facts extracted from the Bun doc

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
