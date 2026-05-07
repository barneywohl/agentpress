# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/EventData/Error/stack`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-stack --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the material-manifest.json file exists at the declared path with all required fields populated

Review gate: The material kit must contain a compact, citation-ready context card that accurately represents the source document's key facts about the Bun Error.stack property, without any fabricated or missing information

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
