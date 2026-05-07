# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/bun/BuildArtifact/formData`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-formdata --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the receipt shows the material-manifest.json at agentpress/material-kits/bun-formdata/material-manifest.json with valid content.

Review gate: The material-manifest.json must contain the exact formData method signatures, exact parameter types, and exact return value shapes extracted from the source document, with no invented content.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
