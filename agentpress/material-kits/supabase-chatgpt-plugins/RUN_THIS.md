# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://supabase.com/docs/guides/ai/examples/building-chatgpt-plugins`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/supabase-chatgpt-plugins --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the proof receipt shows successful materialization without hallucinated endpoints

Review gate: Pass if the kit contains real Supabase auth, database, edge function, and storage context without any unverified claims; fail if any field contains hallucinated endpoint names, status codes, or return shapes

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
