# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/docs/rest-api/sdk/feature-flags/retrieve-the-feature-flags-of-a-deployment`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-feature-flags --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit vercel-feature-flags --claim "Feature flags retrieved successfully" and verify receipt contains SOURCE FACT REQUIRED status code 200 and SOURCE FACT REQUIRED return shape.

Review gate: Pass if receipt shows SOURCE FACT REQUIRED status code 200 and SOURCE FACT REQUIRED return shape with SOURCE FACT REQUIRED fields for flag name, SOURCE FACT REQUIRED status code, and SOURCE FACT REQUIRED callback configuration.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
