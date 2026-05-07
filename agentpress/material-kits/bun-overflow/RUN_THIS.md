# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Runtime/ObjectPreview/overflow`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-overflow --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the receipt shows the overflow condition, error format, and recovery steps were extracted.

Review gate: Pass if the material-manifest.json contains the exact Bun overflow condition, error format, and recovery steps from the source document. Fail if any field contains invented or generic content.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
