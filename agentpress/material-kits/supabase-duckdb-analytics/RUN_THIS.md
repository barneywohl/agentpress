# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://supabase.com/docs/guides/storage/analytics/examples/duckdb`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/supabase-duckdb-analytics --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify that the material kit produces a compact, citation-ready context slice with verified SQL patterns, API endpoints, and auth requirements.

Review gate: Pass if the material kit produces a compact, citation-ready context slice that agents can reference without hallucinating endpoints, and fail if the context slice contains unverified or hallucinated endpoints.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
