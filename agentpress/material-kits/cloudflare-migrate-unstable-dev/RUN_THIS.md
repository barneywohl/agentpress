# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://developers.cloudflare.com/workers/testing/vitest-integration/migration-guides/migrate-from-unstable-dev`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/cloudflare-migrate-unstable-dev --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm receipt shows compact context card with extracted version numbers, CLI commands, and environment variables

Review gate: Pass if receipt confirms compact context card with extracted facts; fail if receipt shows missing or hallucinated facts

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
