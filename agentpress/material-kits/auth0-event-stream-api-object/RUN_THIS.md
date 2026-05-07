# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://auth0.com/docs/customize/actions/explore-triggers/event-stream-triggers/event-stream-api-object`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-event-stream-api-object --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit auth0-event-stream-api-object --json and verify receipt contains compact context for event stream API object

Review gate: Pass if the material kit contains compact, citation-ready context for the Auth0 event stream API object that agents can use without reading the full documentation

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
