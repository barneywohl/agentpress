# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://supabase.com/docs/guides/functions/examples/github-actions`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/supabase-github-actions --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the material-manifest.json exists at agentpress/material-kits/supabase-github-actions/material-manifest.json with the extracted facts.

Review gate: The material kit contains the exact github actions workflow YAML schema, the exact supabase-functions deploy command, and the exact auth configuration steps, with no unverified claims.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
