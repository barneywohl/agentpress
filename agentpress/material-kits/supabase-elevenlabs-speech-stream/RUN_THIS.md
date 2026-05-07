# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://supabase.com/docs/guides/functions/examples/elevenlabs-generate-speech-stream`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/supabase-elevenlabs-speech-stream --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify receipt fields for auth, streaming, and error handling are populated

Review gate: Pass if receipt shows valid auth configuration, streaming response shape, and error code coverage without missing fields

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
