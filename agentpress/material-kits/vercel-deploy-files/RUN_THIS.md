# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://vercel.com/platforms/docs/platform-elements/actions/deploy-files`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-deploy-files --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains deploy commands, environment variables, and build settings

Review gate: Kit must contain SOURCE FACT REQUIRED placeholders for deploy commands, environment variables, and build settings; kit must not contain invented commands

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
