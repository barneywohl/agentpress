# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://developers.cloudflare.com/workers/testing/vitest-integration/migration-guides/migrate-from-miniflare-2`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/cloudflare-migrate-miniflare-2 --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict to verify the card contains specific migration steps, updated commands, and configuration flags

Review gate: Card must contain at least 3 specific SOURCE FACT REQUIRED placeholders for unverified claims, real CLI commands, and no generic filler text

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
