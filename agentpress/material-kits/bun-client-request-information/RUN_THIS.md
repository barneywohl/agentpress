# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/http/ClientRequestEventMap/information`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-client-request-information --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the compact context card contains the event types, type definitions, and error handling without requiring full doc scraping.

Review gate: Pass if the compact context card enables an agent to handle ClientRequest events without visiting the full doc page; fail if the agent still needs to scrape the full doc.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
