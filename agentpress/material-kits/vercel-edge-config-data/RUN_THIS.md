# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/marketplace/get-the-data-of-a-user-provided-edge-config`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-edge-config-data --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the compact context card contains the endpoint, auth, and response schema fields without requiring full doc scraping.

Review gate: Pass if the compact context card enables an agent to retrieve edge config data without visiting the full doc page; fail if the agent still needs to scrape the full doc.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
