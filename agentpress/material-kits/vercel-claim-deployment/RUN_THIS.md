# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/platforms/docs/platform-elements/blocks/claim-deployment`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-claim-deployment --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the vercel-claim-deployment kit passes with no errors.

Review gate: Pass if the material-manifest.json contains the correct Vercel claim-deployment fields and the proof receipt shows successful validation.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
